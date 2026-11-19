use std::cmp::Ordering;
use std::env;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

const W: usize = 192;
const H: usize = 128;
const EPOCHS: usize = 180;
const DEMAND_BLOCK: usize = 15;
const DAMAGE_EPOCH: usize = 90;
const GROWTH_PER_EPOCH: usize = 100;
const DAMAGE_CELLS: usize = 140;
const ENSEMBLE: usize = 8;
const MEDIUM_K: f64 = 0.002;
const MATERIAL_K: f64 = 1.0;
const SINK_CENTERS: [usize; 3] = [28, 64, 100];
const DEMAND_SEQUENCE: [usize; 12] = [0, 1, 2, 0, 2, 1, 0, 2, 1, 2, 0, 1];

#[derive(Clone, Copy, Debug)]
enum Arm {
    Adaptive,
    Fixed,
    CurrentOnly,
}

impl Arm {
    fn name(self) -> &'static str {
        match self {
            Self::Adaptive => "adaptive",
            Self::Fixed => "fixed-cycle",
            Self::CurrentOnly => "current-only",
        }
    }
}

#[derive(Clone, Copy)]
struct Rng64(u64);

impl Rng64 {
    fn new(seed: u64) -> Self {
        Self(seed)
    }
    fn unit(&mut self) -> f64 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut value = self.0;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
        value ^= value >> 31;
        (value >> 11) as f64 / (1_u64 << 53) as f64
    }
}

struct Body {
    occupied: Vec<bool>,
    voltage: Vec<f64>,
    current: Vec<f64>,
    growth_rng: Rng64,
    policy_rng: Rng64,
    values: [f64; 3],
    counts: [usize; 3],
}

struct Metrics {
    delivery: f64,
    peak_current_per_delivery: f64,
    material: usize,
    connected: bool,
}

fn idx(x: usize, y: usize) -> usize {
    y * W + x
}

fn neighbors(cell: usize) -> impl Iterator<Item = usize> {
    let x = cell % W;
    let y = cell / W;
    let mut out = [usize::MAX; 4];
    let mut n = 0;
    if x > 0 {
        out[n] = idx(x - 1, y);
        n += 1;
    }
    if x + 1 < W {
        out[n] = idx(x + 1, y);
        n += 1;
    }
    if y > 0 {
        out[n] = idx(x, y - 1);
        n += 1;
    }
    if y + 1 < H {
        out[n] = idx(x, y + 1);
        n += 1;
    }
    out.into_iter().take(n)
}

impl Body {
    fn new(seed: u64) -> Self {
        let mut occupied = vec![false; W * H];
        for y in (H / 2 - 4)..=(H / 2 + 4) {
            for x in 0..=3 {
                occupied[idx(x, y)] = true;
            }
        }
        let mut voltage = vec![0.0; W * H];
        for y in 0..H {
            for x in 0..W {
                voltage[idx(x, y)] = 1.0 - x as f64 / (W - 1) as f64;
            }
        }
        Self {
            occupied,
            voltage,
            current: vec![0.0; W * H],
            growth_rng: Rng64::new(seed ^ 0x6772_6f77_7468),
            policy_rng: Rng64::new(seed ^ 0x706f_6c69_6379),
            values: [0.0; 3],
            counts: [0; 3],
        }
    }

    fn conductivity(&self, cell: usize) -> f64 {
        if self.occupied[cell] {
            MATERIAL_K
        } else {
            MEDIUM_K
        }
    }

    fn solve(&mut self, sink: usize) -> Metrics {
        let sink_y = SINK_CENTERS[sink];
        for _ in 0..70 {
            for parity in 0..2 {
                for y in 0..H {
                    for x in 0..W {
                        if (x + y) % 2 != parity {
                            continue;
                        }
                        let cell = idx(x, y);
                        if x == 0 && y.abs_diff(H / 2) <= 4 {
                            self.voltage[cell] = 1.0;
                            continue;
                        }
                        if x == W - 1 && y.abs_diff(sink_y) <= 4 {
                            self.voltage[cell] = 0.0;
                            continue;
                        }
                        let mut weighted = 0.0;
                        let mut conductance = 0.0;
                        for other in neighbors(cell) {
                            let face = harmonic(self.conductivity(cell), self.conductivity(other));
                            weighted += face * self.voltage[other];
                            conductance += face;
                        }
                        if conductance > 0.0 {
                            self.voltage[cell] =
                                0.35 * self.voltage[cell] + 0.65 * weighted / conductance;
                        }
                    }
                }
            }
        }
        self.current.fill(0.0);
        for y in 0..H {
            for x in 0..W {
                let cell = idx(x, y);
                let mut sum = 0.0;
                for other in neighbors(cell) {
                    let face = harmonic(self.conductivity(cell), self.conductivity(other));
                    sum += (face * (self.voltage[cell] - self.voltage[other])).abs();
                }
                self.current[cell] = 0.5 * sum;
            }
        }
        let mut delivery = 0.0;
        for y in sink_y.saturating_sub(4)..=(sink_y + 4).min(H - 1) {
            let sink_cell = idx(W - 1, y);
            let inner = idx(W - 2, y);
            delivery += harmonic(self.conductivity(sink_cell), self.conductivity(inner))
                * self.voltage[inner].abs();
        }
        let peak = self.current.iter().copied().fold(0.0_f64, f64::max);
        Metrics {
            delivery,
            peak_current_per_delivery: peak / delivery.max(1.0e-12),
            material: self.occupied.iter().filter(|v| **v).count(),
            connected: connected(&self.occupied, sink),
        }
    }

    fn choose_action(&mut self, arm: Arm, epoch: usize) -> Option<usize> {
        match arm {
            Arm::CurrentOnly => None,
            Arm::Fixed => Some((epoch / 5) % 3),
            Arm::Adaptive => {
                if epoch < 3 {
                    return Some(epoch);
                }
                if self.policy_rng.unit() < 0.08 {
                    return Some((self.policy_rng.unit() * 3.0).floor() as usize % 3);
                }
                let total = self.counts.iter().sum::<usize>() as f64;
                (0..3).max_by(|a, b| {
                    let ua = self.values[*a]
                        + 0.08 * (total.ln() / self.counts[*a].max(1) as f64).sqrt();
                    let ub = self.values[*b]
                        + 0.08 * (total.ln() / self.counts[*b].max(1) as f64).sqrt();
                    ua.partial_cmp(&ub).unwrap_or(Ordering::Equal)
                })
            }
        }
    }

    fn update_action(&mut self, action: Option<usize>, reward: f64) {
        if let Some(action) = action {
            self.counts[action] += 1;
            let n = self.counts[action] as f64;
            self.values[action] += (reward - self.values[action]) / n;
        }
    }

    fn grow(&mut self, action: Option<usize>) {
        let max_current = self
            .current
            .iter()
            .copied()
            .fold(0.0_f64, f64::max)
            .max(1.0e-12);
        for _ in 0..GROWTH_PER_EPOCH {
            let mut candidates = Vec::new();
            let mut total = 0.0;
            for cell in 0..(W * H) {
                if self.occupied[cell] || !neighbors(cell).any(|n| self.occupied[n]) {
                    continue;
                }
                let x = cell % W;
                let y = cell / W;
                let current = self.current[cell] / max_current;
                let optical = action
                    .map(|a| {
                        let dy = (y as f64 - SINK_CENTERS[a] as f64) / 10.0;
                        (-0.5 * dy * dy).exp() * (0.35 + 0.65 * x as f64 / (W - 1) as f64)
                    })
                    .unwrap_or(0.0);
                let weight = 0.002 + current.powf(1.2) * (1.0 + 3.0 * optical);
                total += weight;
                candidates.push((cell, weight));
            }
            if total <= 0.0 {
                break;
            }
            let mut draw = self.growth_rng.unit() * total;
            let mut chosen = candidates.last().unwrap().0;
            for (cell, weight) in candidates {
                if draw <= weight {
                    chosen = cell;
                    break;
                }
                draw -= weight;
            }
            self.occupied[chosen] = true;
        }
    }

    fn damage(&mut self) -> usize {
        let mut cells: Vec<_> = (0..W * H)
            .filter(|cell| self.occupied[*cell] && (cell % W).abs_diff(W / 2) <= 4)
            .collect();
        cells.sort_by(|a, b| {
            self.current[*b]
                .partial_cmp(&self.current[*a])
                .unwrap_or(Ordering::Equal)
        });
        let removed = cells.len().min(DAMAGE_CELLS);
        for cell in cells.into_iter().take(removed) {
            self.occupied[cell] = false;
        }
        removed
    }
}

fn harmonic(a: f64, b: f64) -> f64 {
    2.0 * a * b / (a + b).max(1.0e-12)
}

fn connected(occupied: &[bool], sink: usize) -> bool {
    let mut seen = vec![false; W * H];
    let mut queue = std::collections::VecDeque::new();
    for y in (H / 2 - 4)..=(H / 2 + 4) {
        let cell = idx(0, y);
        if occupied[cell] {
            seen[cell] = true;
            queue.push_back(cell);
        }
    }
    let sink_y = SINK_CENTERS[sink];
    while let Some(cell) = queue.pop_front() {
        let x = cell % W;
        let y = cell / W;
        if x == W - 1 && y.abs_diff(sink_y) <= 4 {
            return true;
        }
        for other in neighbors(cell) {
            if occupied[other] && !seen[other] {
                seen[other] = true;
                queue.push_back(other);
            }
        }
    }
    false
}

fn run_arm(arm: Arm, seed: u64, frames: Option<&Path>, writer: &mut impl Write) {
    let mut body = Body::new(seed);
    let mut pre_damage_delivery = 0.0;
    let mut recovery_epoch: Option<usize> = None;
    for epoch in 0..=EPOCHS {
        let sink = DEMAND_SEQUENCE[(epoch / DEMAND_BLOCK).min(DEMAND_SEQUENCE.len() - 1)];
        let before = body.solve(sink);
        let mut removed = 0;
        if epoch == DAMAGE_EPOCH {
            pre_damage_delivery = before.delivery;
            removed = body.damage();
        }
        let damaged = if removed > 0 {
            body.solve(sink)
        } else {
            before
        };
        let action = body.choose_action(arm, epoch);
        if epoch < EPOCHS {
            body.grow(action);
        }
        let after = body.solve(sink);
        let delivery_gain = (after.delivery / damaged.delivery.max(1.0e-12)).ln();
        let concentration_relief =
            (damaged.peak_current_per_delivery / after.peak_current_per_delivery.max(1.0e-12)).ln();
        let reward = delivery_gain + 0.75 * concentration_relief;
        body.update_action(action, reward);
        if epoch >= DAMAGE_EPOCH
            && recovery_epoch.is_none()
            && after.delivery >= 0.90 * pre_damage_delivery
        {
            recovery_epoch = Some(epoch);
        }
        writeln!(
            writer,
            "{}\t{}\t{}\t{}\t{}\t{}\t{:.12}\t{:.12}\t{}\t{}\t{}\t{}",
            arm.name(),
            seed,
            epoch,
            sink,
            action
                .map(|v| v.to_string())
                .unwrap_or_else(|| "none".into()),
            removed,
            after.delivery,
            after.peak_current_per_delivery,
            after.material,
            after.connected as u8,
            recovery_epoch
                .map(|v| v.to_string())
                .unwrap_or_else(|| "none".into()),
            epoch >= DAMAGE_EPOCH
        )
        .unwrap();
        if let Some(directory) = frames {
            write_pgm(
                &directory.join(format!("{}-{:03}.pgm", arm.name(), epoch)),
                &body.occupied,
            )
            .unwrap();
        }
    }
}

fn write_pgm(path: &Path, occupied: &[bool]) -> std::io::Result<()> {
    let mut writer = BufWriter::new(File::create(path)?);
    write!(writer, "P5\n{} {}\n255\n", W, H)?;
    for value in occupied {
        writer.write_all(&[if *value { 255 } else { 0 }])?;
    }
    Ok(())
}

fn main() {
    let output = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("output"));
    fs::create_dir_all(output.join("frames")).unwrap();
    let mut writer = BufWriter::new(File::create(output.join("metrics.tsv")).unwrap());
    writeln!(writer, "arm\tseed\tepoch\tsink\taction\tremoved\tdelivery\tpeak_current_per_delivery\tmaterial\tconnected\trecovery_epoch\tpost_damage").unwrap();
    for offset in 0..ENSEMBLE {
        let seed = 319 + offset as u64;
        for arm in [Arm::Adaptive, Arm::Fixed, Arm::CurrentOnly] {
            let frames = if seed == 319 {
                Some(output.join("frames"))
            } else {
                None
            };
            run_arm(arm, seed, frames.as_deref(), &mut writer);
        }
    }
    println!(
        "output={} arms=3 seeds={} epochs={}",
        output.display(),
        ENSEMBLE,
        EPOCHS
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matched_bodies_start_identically() {
        let left = Body::new(319);
        let right = Body::new(319);
        assert_eq!(left.occupied, right.occupied);
        assert_eq!(left.voltage, right.voltage);
        assert_eq!(left.growth_rng.0, right.growth_rng.0);
        assert_eq!(left.policy_rng.0, right.policy_rng.0);
    }

    #[test]
    fn policy_draws_leave_growth_stream_unchanged() {
        let mut body = Body::new(319);
        let mut control = Body::new(319);
        for epoch in 0..20 {
            let _ = body.choose_action(Arm::Adaptive, epoch);
        }
        assert_eq!(body.growth_rng.unit(), control.growth_rng.unit());
    }

    #[test]
    fn demand_schedule_exercises_every_sink() {
        let sinks: std::collections::HashSet<_> = DEMAND_SEQUENCE.into_iter().collect();
        assert_eq!(sinks.len(), 3);
        assert!(sinks.contains(&0) && sinks.contains(&1) && sinks.contains(&2));
    }

    #[test]
    fn source_material_is_connected_at_initialization() {
        let body = Body::new(319);
        assert_eq!(body.occupied.iter().filter(|value| **value).count(), 36);
        for y in (H / 2 - 4)..=(H / 2 + 4) {
            for x in 0..=3 {
                assert!(body.occupied[idx(x, y)]);
            }
        }
    }
}
