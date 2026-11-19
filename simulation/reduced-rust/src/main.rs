use std::collections::VecDeque;
use std::env;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::Duration;

const W: usize = 192;
const H: usize = 128;

#[derive(Clone, Copy)]
enum LightMode {
    Band,
    Cherenkov,
}

impl LightMode {
    fn name(self) -> &'static str {
        match self {
            Self::Band => "band",
            Self::Cherenkov => "cherenkov",
        }
    }
}

#[derive(Clone, Copy)]
struct Config {
    steps: usize,
    seed: u64,
    drive: f64,
    light_gain: f64,
    light_center: f64,
    light_slope: f64,
    follow_gain: f64,
    frame_every: usize,
    frame_delay_ms: u64,
    cycle_frame_every: usize,
    light_mode: LightMode,
    refractive_index: f64,
    beta: f64,
    source_x: f64,
    repair_cut_radius: usize,
    repair_steps: usize,
    repair_cycles: usize,
    repair_transect: bool,
    dual_seed: bool,
    mobility: f64,
}

struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self {
        Self(seed.max(1))
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }

    fn unit(&mut self) -> f64 {
        (self.next_u64() as f64) / (u64::MAX as f64)
    }
}

struct Sim {
    metal: Vec<bool>,
    species: Vec<u8>,
    phi: Vec<f64>,
    concentration: Vec<f64>,
    rng: Rng,
    cfg: Config,
    light_center: f64,
}

impl Sim {
    fn new(cfg: Config) -> Self {
        let mut sim = Self {
            metal: vec![false; W * H],
            species: vec![0; W * H],
            phi: vec![0.0; W * H],
            concentration: vec![1.0; W * H],
            rng: Rng::new(cfg.seed),
            cfg,
            light_center: cfg.light_center,
        };

        let seeds = if cfg.dual_seed {
            vec![(H / 3, 1u8), (2 * H / 3, 2u8)]
        } else {
            vec![(H / 2, 1u8)]
        };
        for (cy, species) in seeds {
            for x in 0..=3 {
                for y in cy.saturating_sub(2)..=(cy + 2).min(H - 1) {
                    let i = Self::idx(x, y);
                    sim.metal[i] = true;
                    sim.species[i] = species;
                    sim.concentration[i] = 0.0;
                }
            }
        }
        sim
    }

    #[inline]
    fn idx(x: usize, y: usize) -> usize {
        y * W + x
    }

    fn neighbors8(x: usize, y: usize) -> impl Iterator<Item = (usize, usize)> {
        let x0 = x.saturating_sub(1);
        let y0 = y.saturating_sub(1);
        let x1 = (x + 1).min(W - 1);
        let y1 = (y + 1).min(H - 1);
        (y0..=y1).flat_map(move |yy| {
            (x0..=x1).filter_map(move |xx| {
                if xx == x && yy == y {
                    None
                } else {
                    Some((xx, yy))
                }
            })
        })
    }

    fn source_connected(&self) -> Vec<bool> {
        let mut connected = vec![false; W * H];
        let mut queue = VecDeque::new();
        for y in 0..H {
            let i = Self::idx(0, y);
            if self.metal[i] {
                connected[i] = true;
                queue.push_back((0, y));
            }
        }
        while let Some((x, y)) = queue.pop_front() {
            for (xx, yy) in Self::neighbors8(x, y) {
                let i = Self::idx(xx, yy);
                if self.metal[i] && !connected[i] {
                    connected[i] = true;
                    queue.push_back((xx, yy));
                }
            }
        }
        connected
    }

    fn solve_potential(&mut self, iterations: usize) {
        let connected = self.source_connected();
        for y in 0..H {
            self.phi[Self::idx(0, y)] = 0.0;
            self.phi[Self::idx(W - 1, y)] = 1.0;
        }
        for (i, is_connected) in connected.iter().copied().enumerate() {
            if is_connected {
                self.phi[i] = 0.0;
            }
        }

        for _ in 0..iterations {
            for y in 0..H {
                let ym = y.saturating_sub(1);
                let yp = (y + 1).min(H - 1);
                for x in 1..W - 1 {
                    let i = Self::idx(x, y);
                    if connected[i] {
                        self.phi[i] = 0.0;
                        continue;
                    }
                    self.phi[i] = 0.25
                        * (self.phi[Self::idx(x - 1, y)]
                            + self.phi[Self::idx(x + 1, y)]
                            + self.phi[Self::idx(x, ym)]
                            + self.phi[Self::idx(x, yp)]);
                }
            }
        }
    }

    fn diffuse(&mut self, substeps: usize) {
        let d = 0.12;
        let dt = 0.18;
        let mut next = self.concentration.clone();
        for _ in 0..substeps {
            for y in 0..H {
                let ym = y.saturating_sub(1);
                let yp = (y + 1).min(H - 1);
                for x in 1..W - 1 {
                    let i = Self::idx(x, y);
                    if self.metal[i] {
                        next[i] = 0.0;
                        continue;
                    }
                    let lap = self.concentration[Self::idx(x - 1, y)]
                        + self.concentration[Self::idx(x + 1, y)]
                        + self.concentration[Self::idx(x, ym)]
                        + self.concentration[Self::idx(x, yp)]
                        - 4.0 * self.concentration[i];
                    next[i] = (self.concentration[i] + d * dt * lap).clamp(0.0, 1.0);
                }
            }
            for y in 0..H {
                next[Self::idx(W - 1, y)] = 1.0;
            }
            std::mem::swap(&mut self.concentration, &mut next);
        }
    }

    fn light_at(&self, x: usize, y: usize) -> f64 {
        if self.cfg.light_gain <= 0.0 {
            return 1.0;
        }
        let xn = x as f64 / (W - 1) as f64;
        let yn = y as f64 / (H - 1) as f64;
        match self.cfg.light_mode {
            LightMode::Band => {
                let center = self.light_center + self.cfg.light_slope * (xn - 0.5);
                let sigma = 0.12;
                1.0 + self.cfg.light_gain * (-(yn - center).powi(2) / (2.0 * sigma * sigma)).exp()
            }
            LightMode::Cherenkov => {
                let threshold = self.cfg.beta * self.cfg.refractive_index;
                if threshold <= 1.0 || xn < self.cfg.source_x {
                    return 1.0;
                }
                let theta = (1.0 / threshold).acos();
                let cone_y = theta.tan() * (xn - self.cfg.source_x);
                let distance = ((yn - self.light_center).abs() - cone_y).abs();
                let sigma = 0.025;
                1.0 + self.cfg.light_gain * (-(distance * distance) / (2.0 * sigma * sigma)).exp()
            }
        }
    }

    fn field_at(&self, x: usize, y: usize) -> f64 {
        let xm = x.saturating_sub(1);
        let xp = (x + 1).min(W - 1);
        let ym = y.saturating_sub(1);
        let yp = (y + 1).min(H - 1);
        let gx = 0.5 * (self.phi[Self::idx(xp, y)] - self.phi[Self::idx(xm, y)]);
        let gy = 0.5 * (self.phi[Self::idx(x, yp)] - self.phi[Self::idx(x, ym)]);
        (gx * gx + gy * gy).sqrt()
    }

    fn candidates(&self) -> Vec<(usize, f64)> {
        let connected = self.source_connected();
        let mut out = Vec::new();
        for y in 1..H - 1 {
            for x in 1..W - 1 {
                let i = Self::idx(x, y);
                if self.metal[i]
                    || !Self::neighbors8(x, y).any(|(xx, yy)| connected[Self::idx(xx, yy)])
                {
                    continue;
                }
                let field = self.field_at(x, y);
                let c = self.concentration[i];
                let light = self.light_at(x, y);
                let forward = 0.25 + 0.75 * (x as f64 / (W - 1) as f64);
                let weight =
                    c * light * forward * (1e-6 + field).powf(0.65 + 1.25 * self.cfg.drive);
                if weight.is_finite() && weight > 0.0 {
                    out.push((i, weight));
                }
            }
        }
        out
    }

    fn grow_one(&mut self) -> bool {
        let mobility = self.cfg.mobility.clamp(0.0, 1.0);
        if mobility < 1.0 && self.rng.unit() > mobility {
            return true;
        }
        let candidates = self.candidates();
        let total: f64 = candidates.iter().map(|(_, w)| *w).sum();
        if total <= 0.0 {
            return false;
        }
        let mut pick = self.rng.unit() * total;
        let mut chosen = candidates[0].0;
        for (i, w) in candidates {
            if pick <= w {
                chosen = i;
                break;
            }
            pick -= w;
        }
        self.metal[chosen] = true;
        let x = chosen % W;
        let y = chosen / W;
        let mut counts = [0usize; 3];
        for (xx, yy) in Self::neighbors8(x, y) {
            let species = self.species[Self::idx(xx, yy)] as usize;
            if species > 0 && species < counts.len() {
                counts[species] += 1;
            }
        }
        self.species[chosen] = if counts[1] > counts[2] {
            1
        } else if counts[2] > counts[1] {
            2
        } else if self.rng.unit() < 0.5 {
            1
        } else {
            2
        };
        self.concentration[chosen] = 0.0;
        for (xx, yy) in Self::neighbors8(x, y) {
            let j = Self::idx(xx, yy);
            self.concentration[j] *= 0.86;
        }
        true
    }

    fn frontier(&self) -> usize {
        let connected = self.source_connected();
        connected
            .iter()
            .enumerate()
            .filter_map(|(i, m)| m.then_some(i % W))
            .max()
            .unwrap_or(0)
    }

    fn bridge(&self) -> bool {
        self.frontier() >= W - 2
    }

    fn metal_count(&self) -> usize {
        self.metal.iter().filter(|&&m| m).count()
    }

    fn species_count(&self, species: u8) -> usize {
        self.species.iter().filter(|&&s| s == species).count()
    }

    fn cut_near_midpoint(&mut self, radius: usize) -> usize {
        let connected = self.source_connected();
        let mut target = None;
        let mut best = usize::MAX;
        for (i, is_connected) in connected.iter().copied().enumerate() {
            if !is_connected {
                continue;
            }
            let x = i % W;
            let y = i / W;
            if x <= 3 || x >= W - 4 {
                continue;
            }
            let score = x.abs_diff(W / 2) * 10 + y.abs_diff(H / 2);
            if score < best {
                best = score;
                target = Some((x, y));
            }
        }
        let Some((x, y)) = target else {
            return 0;
        };
        let mut removed = 0;
        for yy in y.saturating_sub(radius)..=(y + radius).min(H - 1) {
            for xx in x.saturating_sub(radius)..=(x + radius).min(W - 1) {
                let i = Self::idx(xx, yy);
                if self.metal[i] {
                    self.metal[i] = false;
                    self.species[i] = 0;
                    self.concentration[i] = 1.0;
                    removed += 1;
                }
            }
        }
        removed
    }

    fn cut_vertical_transect(&mut self, radius: usize) -> usize {
        let mut removed = 0;
        for y in 0..H {
            for x in (W / 2).saturating_sub(radius)..=(W / 2 + radius).min(W - 1) {
                let i = Self::idx(x, y);
                if self.metal[i] {
                    self.metal[i] = false;
                    self.species[i] = 0;
                    self.concentration[i] = 1.0;
                    removed += 1;
                }
            }
        }
        removed
    }

    fn update_light_from_frontier(&mut self) {
        let gain = self.cfg.follow_gain.clamp(0.0, 1.0);
        if gain == 0.0 {
            return;
        }
        let front = self.frontier();
        let x0 = front.saturating_sub(2);
        let connected = self.source_connected();
        let mut y_sum = 0.0;
        let mut n = 0usize;
        for y in 0..H {
            for x in x0..=front {
                if connected[Self::idx(x, y)] {
                    y_sum += y as f64 / (H - 1) as f64;
                    n += 1;
                }
            }
        }
        if n > 0 {
            let observed = y_sum / n as f64;
            self.light_center += gain * (observed - self.light_center);
        }
    }
}

fn write_pgm(path: &Path, values: &[u8]) -> std::io::Result<()> {
    let mut out = BufWriter::new(File::create(path)?);
    writeln!(out, "P5\n{W} {H}\n255")?;
    out.write_all(values)
}

fn write_live_ppm(path: &Path, sim: &Sim) -> std::io::Result<()> {
    let temporary = path.with_extension("tmp.ppm");
    let mut out = BufWriter::new(File::create(&temporary)?);
    writeln!(out, "P6\n{W} {H}\n255")?;
    let light_scale = sim.cfg.light_gain.max(1e-9);
    for y in 0..H {
        for x in 0..W {
            let i = Sim::idx(x, y);
            let pixel = if sim.metal[i] {
                match sim.species[i] {
                    1 => [225, 193, 110],
                    2 => [121, 215, 255],
                    _ => [255, 255, 245],
                }
            } else {
                let light = ((sim.light_at(x, y) - 1.0) / light_scale).clamp(0.0, 1.0);
                let field = sim.phi[i].clamp(0.0, 1.0);
                [
                    (18.0 + 38.0 * field) as u8,
                    (20.0 + 90.0 * light) as u8,
                    (28.0 + 190.0 * light) as u8,
                ]
            };
            out.write_all(&pixel)?;
        }
    }
    out.flush()?;
    fs::rename(temporary, path)
}

fn parse_args() -> (Config, PathBuf, Option<PathBuf>, Option<PathBuf>) {
    let mut cfg = Config {
        steps: 600,
        seed: 319,
        drive: 0.7,
        light_gain: 0.0,
        light_center: 0.5,
        light_slope: 0.0,
        follow_gain: 0.0,
        frame_every: 5,
        frame_delay_ms: 0,
        cycle_frame_every: 0,
        light_mode: LightMode::Band,
        refractive_index: 1.33,
        beta: 0.99,
        source_x: 0.05,
        repair_cut_radius: 0,
        repair_steps: 0,
        repair_cycles: 1,
        repair_transect: false,
        dual_seed: false,
        mobility: 1.0,
    };
    let mut output = PathBuf::from("../output/baseline");
    let mut live_frame = None;
    let mut frame_dir = None;
    let args: Vec<String> = env::args().collect();
    let mut i = 1;
    while i + 1 < args.len() {
        match args[i].as_str() {
            "--steps" => cfg.steps = args[i + 1].parse().expect("valid --steps"),
            "--seed" => cfg.seed = args[i + 1].parse().expect("valid --seed"),
            "--drive" => cfg.drive = args[i + 1].parse().expect("valid --drive"),
            "--light-gain" => cfg.light_gain = args[i + 1].parse().expect("valid --light-gain"),
            "--light-center" => {
                cfg.light_center = args[i + 1].parse().expect("valid --light-center")
            }
            "--light-slope" => cfg.light_slope = args[i + 1].parse().expect("valid --light-slope"),
            "--follow-gain" => cfg.follow_gain = args[i + 1].parse().expect("valid --follow-gain"),
            "--frame-every" => cfg.frame_every = args[i + 1].parse().expect("valid --frame-every"),
            "--frame-delay-ms" => {
                cfg.frame_delay_ms = args[i + 1].parse().expect("valid --frame-delay-ms")
            }
            "--cycle-frame-every" => {
                cfg.cycle_frame_every = args[i + 1].parse().expect("valid --cycle-frame-every")
            }
            "--light-mode" => {
                cfg.light_mode = match args[i + 1].as_str() {
                    "band" => LightMode::Band,
                    "cherenkov" => LightMode::Cherenkov,
                    value => panic!("unknown --light-mode: {value}"),
                }
            }
            "--refractive-index" => {
                cfg.refractive_index = args[i + 1].parse().expect("valid --refractive-index")
            }
            "--beta" => cfg.beta = args[i + 1].parse().expect("valid --beta"),
            "--source-x" => cfg.source_x = args[i + 1].parse().expect("valid --source-x"),
            "--repair-cut-radius" => {
                cfg.repair_cut_radius = args[i + 1].parse().expect("valid --repair-cut-radius")
            }
            "--repair-steps" => {
                cfg.repair_steps = args[i + 1].parse().expect("valid --repair-steps")
            }
            "--repair-cycles" => {
                cfg.repair_cycles = args[i + 1].parse().expect("valid --repair-cycles")
            }
            "--repair-transect" => {
                cfg.repair_transect = match args[i + 1].as_str() {
                    "true" => true,
                    "false" => false,
                    value => panic!("invalid --repair-transect: {value}"),
                }
            }
            "--dual-seed" => {
                cfg.dual_seed = match args[i + 1].as_str() {
                    "true" => true,
                    "false" => false,
                    value => panic!("invalid --dual-seed: {value}"),
                }
            }
            "--mobility" => cfg.mobility = args[i + 1].parse().expect("valid --mobility"),
            "--live-frame" => live_frame = Some(PathBuf::from(&args[i + 1])),
            "--frame-dir" => frame_dir = Some(PathBuf::from(&args[i + 1])),
            "--output" => output = PathBuf::from(&args[i + 1]),
            unknown => panic!("unknown argument: {unknown}"),
        }
        i += 2;
    }
    (cfg, output, live_frame, frame_dir)
}

fn main() -> std::io::Result<()> {
    let (cfg, output, live_frame, frame_dir) = parse_args();
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut sim = Sim::new(cfg);
    if let Some(path) = &frame_dir {
        fs::create_dir_all(path)?;
    }
    let mut frame_index = 0usize;
    let csv_path = output.with_extension("csv");
    let mut log = BufWriter::new(File::create(csv_path)?);
    writeln!(log, "step,metal_cells,frontier_x,light_center,bridged")?;

    let events = (1.0 + 2.0 * cfg.drive.clamp(0.0, 1.5)).round() as usize;
    let mut steps_completed = 0;
    for step in 0..cfg.steps {
        steps_completed = step + 1;
        sim.solve_potential(45);
        sim.diffuse(3);
        for _ in 0..events.max(1) {
            if !sim.grow_one() {
                break;
            }
        }
        sim.update_light_from_frontier();
        if step % 10 == 0 || sim.bridge() {
            writeln!(
                log,
                "{step},{},{},{:.6},{}",
                sim.metal_count(),
                sim.frontier(),
                sim.light_center,
                sim.bridge()
            )?;
        }
        if step % cfg.frame_every.max(1) == 0 || sim.bridge() {
            if let Some(path) = &live_frame {
                write_live_ppm(path, &sim)?;
            }
            if let Some(path) = &frame_dir {
                write_live_ppm(&path.join(format!("frame-{frame_index:05}.ppm")), &sim)?;
                frame_index += 1;
            }
            if cfg.frame_delay_ms > 0 {
                thread::sleep(Duration::from_millis(cfg.frame_delay_ms));
            }
        }
        if sim.bridge() {
            break;
        }
    }

    let bridge_metal = sim.metal_count();
    let mut cut_removed = 0;
    let mut repair_steps_completed = 0;
    let mut repair_added = 0;
    let mut repair_cycles_completed = 0;
    let mut repair_failures = 0;
    let mut repaired = sim.bridge();
    if cfg.repair_cut_radius > 0 && repaired {
        let repair_csv_path = output.with_extension("repair.csv");
        let mut repair_log = BufWriter::new(File::create(repair_csv_path)?);
        writeln!(repair_log, "cycle,removed,steps,added,repaired,metal_cells")?;
        for cycle in 0..cfg.repair_cycles {
            if !repaired {
                break;
            }
            let removed = if cfg.repair_transect {
                sim.cut_vertical_transect(cfg.repair_cut_radius)
            } else {
                sim.cut_near_midpoint(cfg.repair_cut_radius)
            };
            cut_removed += removed;
            let after_cut = sim.metal_count();
            repaired = sim.bridge();
            let mut cycle_steps = 0;
            for repair_step in 0..cfg.repair_steps {
                if repaired {
                    break;
                }
                cycle_steps = repair_step + 1;
                sim.solve_potential(45);
                sim.diffuse(3);
                for _ in 0..events.max(1) {
                    if !sim.grow_one() {
                        break;
                    }
                }
                sim.update_light_from_frontier();
                repaired = sim.bridge();
                if repair_step % cfg.frame_every.max(1) == 0 || repaired {
                    if let Some(path) = &live_frame {
                        write_live_ppm(path, &sim)?;
                    }
                    if cfg.cycle_frame_every == 0 {
                        if let Some(path) = &frame_dir {
                            write_live_ppm(
                                &path.join(format!("frame-{frame_index:05}.ppm")),
                                &sim,
                            )?;
                            frame_index += 1;
                        }
                    }
                    if cfg.frame_delay_ms > 0 {
                        thread::sleep(Duration::from_millis(cfg.frame_delay_ms));
                    }
                }
            }
            let added = sim.metal_count().saturating_sub(after_cut);
            repair_steps_completed += cycle_steps;
            repair_added += added;
            repair_cycles_completed += 1;
            if !repaired {
                repair_failures += 1;
            }
            writeln!(
                repair_log,
                "{},{},{},{},{},{}",
                cycle + 1,
                removed,
                cycle_steps,
                added,
                repaired,
                sim.metal_count()
            )?;
            if cfg.cycle_frame_every > 0 && ((cycle + 1) % cfg.cycle_frame_every == 0 || cycle == 0)
            {
                if let Some(path) = &frame_dir {
                    write_live_ppm(&path.join(format!("frame-{frame_index:05}.ppm")), &sim)?;
                    frame_index += 1;
                }
            }
        }
    }

    sim.solve_potential(100);
    let metal: Vec<u8> = sim.metal.iter().map(|m| if *m { 255 } else { 0 }).collect();
    let potential: Vec<u8> = sim
        .phi
        .iter()
        .map(|v| (255.0 * v.clamp(0.0, 1.0)).round() as u8)
        .collect();
    write_pgm(&output.with_extension("metal.pgm"), &metal)?;
    write_pgm(&output.with_extension("potential.pgm"), &potential)?;

    println!(
        "steps_completed={} step_budget={} seed={} drive={:.3} mobility={:.3} dual_seed={} light_mode={} light_gain={:.3} follow_gain={:.3} light_center={:.6} bridge_metal={} metal={} species_1={} species_2={} frontier={} bridged={} cut_removed={} repair_steps_completed={} repair_added={} repair_cycles_completed={} repair_failures={} repaired={}",
        steps_completed,
        cfg.steps,
        cfg.seed,
        cfg.drive,
        cfg.mobility,
        cfg.dual_seed,
        cfg.light_mode.name(),
        cfg.light_gain,
        cfg.follow_gain,
        sim.light_center,
        bridge_metal,
        sim.metal_count(),
        sim.species_count(1),
        sim.species_count(2),
        sim.frontier(),
        sim.bridge(),
        cut_removed,
        repair_steps_completed,
        repair_added,
        repair_cycles_completed,
        repair_failures,
        repaired
    );
    Ok(())
}
