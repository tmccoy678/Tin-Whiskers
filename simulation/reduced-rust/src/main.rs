use std::env;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

const W: usize = 192;
const H: usize = 128;

#[derive(Clone, Copy)]
struct Config {
    steps: usize,
    seed: u64,
    drive: f64,
    light_gain: f64,
    light_center: f64,
    light_slope: f64,
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
    phi: Vec<f64>,
    concentration: Vec<f64>,
    rng: Rng,
    cfg: Config,
}

impl Sim {
    fn new(cfg: Config) -> Self {
        let mut sim = Self {
            metal: vec![false; W * H],
            phi: vec![0.0; W * H],
            concentration: vec![1.0; W * H],
            rng: Rng::new(cfg.seed),
            cfg,
        };

        let cy = H / 2;
        for x in 0..=3 {
            for y in cy.saturating_sub(2)..=(cy + 2).min(H - 1) {
                let i = Self::idx(x, y);
                sim.metal[i] = true;
                sim.concentration[i] = 0.0;
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

    fn solve_potential(&mut self, iterations: usize) {
        for y in 0..H {
            self.phi[Self::idx(0, y)] = 0.0;
            self.phi[Self::idx(W - 1, y)] = 1.0;
        }
        for (i, is_metal) in self.metal.iter().copied().enumerate() {
            if is_metal {
                self.phi[i] = 0.0;
            }
        }

        for _ in 0..iterations {
            for y in 0..H {
                let ym = y.saturating_sub(1);
                let yp = (y + 1).min(H - 1);
                for x in 1..W - 1 {
                    let i = Self::idx(x, y);
                    if self.metal[i] {
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
        let center = self.cfg.light_center + self.cfg.light_slope * (xn - 0.5);
        let sigma = 0.12;
        1.0 + self.cfg.light_gain * (-(yn - center).powi(2) / (2.0 * sigma * sigma)).exp()
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
        let mut out = Vec::new();
        for y in 1..H - 1 {
            for x in 1..W - 1 {
                let i = Self::idx(x, y);
                if self.metal[i]
                    || !Self::neighbors8(x, y).any(|(xx, yy)| self.metal[Self::idx(xx, yy)])
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
        self.concentration[chosen] = 0.0;
        let x = chosen % W;
        let y = chosen / W;
        for (xx, yy) in Self::neighbors8(x, y) {
            let j = Self::idx(xx, yy);
            self.concentration[j] *= 0.86;
        }
        true
    }

    fn frontier(&self) -> usize {
        self.metal
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
}

fn write_pgm(path: &Path, values: &[u8]) -> std::io::Result<()> {
    let mut out = BufWriter::new(File::create(path)?);
    writeln!(out, "P5\n{W} {H}\n255")?;
    out.write_all(values)
}

fn parse_args() -> (Config, PathBuf) {
    let mut cfg = Config {
        steps: 600,
        seed: 319,
        drive: 0.7,
        light_gain: 0.0,
        light_center: 0.5,
        light_slope: 0.0,
    };
    let mut output = PathBuf::from("../output/baseline");
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
            "--output" => output = PathBuf::from(&args[i + 1]),
            unknown => panic!("unknown argument: {unknown}"),
        }
        i += 2;
    }
    (cfg, output)
}

fn main() -> std::io::Result<()> {
    let (cfg, output) = parse_args();
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut sim = Sim::new(cfg);
    let csv_path = output.with_extension("csv");
    let mut log = BufWriter::new(File::create(csv_path)?);
    writeln!(log, "step,metal_cells,frontier_x,bridged")?;

    let events = (1.0 + 2.0 * cfg.drive.clamp(0.0, 1.5)).round() as usize;
    for step in 0..cfg.steps {
        sim.solve_potential(45);
        sim.diffuse(3);
        for _ in 0..events.max(1) {
            if !sim.grow_one() {
                break;
            }
        }
        if step % 10 == 0 || sim.bridge() {
            writeln!(
                log,
                "{step},{},{},{}",
                sim.metal_count(),
                sim.frontier(),
                sim.bridge()
            )?;
        }
        if sim.bridge() {
            break;
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
        "steps={} seed={} drive={:.3} light_gain={:.3} metal={} frontier={} bridged={}",
        cfg.steps,
        cfg.seed,
        cfg.drive,
        cfg.light_gain,
        sim.metal_count(),
        sim.frontier(),
        sim.bridge()
    );
    Ok(())
}
