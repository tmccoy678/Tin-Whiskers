use std::collections::HashSet;
use std::env;
use std::f64::consts::PI;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

const W: usize = 192;
const H: usize = 128;
const BARRIER_X: usize = 36;
const SLIT_CENTERS: [usize; 2] = [48, 80];
const SLIT_HALF_WIDTH: usize = 4;
const WAVELENGTH_CELLS: f64 = 8.0;
const STEPS: usize = 12_000;
const SWITCH_STEP: usize = 6_000;
const FRAME_EVERY: usize = 120;
const ENSEMBLE_SEEDS: usize = 32;

#[derive(Clone, Copy, Debug)]
enum Condition {
    Coherent,
    PathTagged,
    CoherentToTagged,
    TaggedToCoherent,
}

impl Condition {
    fn name(self) -> &'static str {
        match self {
            Self::Coherent => "coherent",
            Self::PathTagged => "path-tagged",
            Self::CoherentToTagged => "coherent-to-tagged",
            Self::TaggedToCoherent => "tagged-to-coherent",
        }
    }

    fn coherent_at(self, step: usize) -> bool {
        match self {
            Self::Coherent => true,
            Self::PathTagged => false,
            Self::CoherentToTagged => step < SWITCH_STEP,
            Self::TaggedToCoherent => step >= SWITCH_STEP,
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

struct Fields {
    coherent: Vec<f64>,
    tagged: Vec<f64>,
}

struct ResultRow {
    condition: &'static str,
    seed: u64,
    connected_step: Option<usize>,
    occupied: usize,
    coherent_alignment: f64,
    tagged_alignment: f64,
    upper_slit_cells: usize,
    lower_slit_cells: usize,
}

fn index(x: usize, y: usize) -> usize {
    y * W + x
}

fn is_slit(y: usize) -> bool {
    SLIT_CENTERS
        .iter()
        .any(|center| y.abs_diff(*center) <= SLIT_HALF_WIDTH)
}

fn blocked(x: usize, y: usize) -> bool {
    x == BARRIER_X && !is_slit(y)
}

fn emitters(center: usize) -> impl Iterator<Item = usize> {
    (center - SLIT_HALF_WIDTH)..=(center + SLIT_HALF_WIDTH)
}

fn complex_field(x: usize, y: usize, center: usize) -> (f64, f64) {
    if x <= BARRIER_X {
        let dy = y as f64 - center as f64;
        let envelope = (-0.5 * (dy / 12.0).powi(2)).exp();
        return (envelope, 0.0);
    }
    let k = 2.0 * PI / WAVELENGTH_CELLS;
    let mut real = 0.0;
    let mut imaginary = 0.0;
    for emitter_y in emitters(center) {
        let dx = (x - BARRIER_X) as f64;
        let dy = y as f64 - emitter_y as f64;
        let distance = (dx * dx + dy * dy).sqrt().max(1.0);
        let amplitude = 1.0 / distance.sqrt();
        real += amplitude * (k * distance).cos();
        imaginary += amplitude * (k * distance).sin();
    }
    (real, imaginary)
}

fn make_fields() -> Fields {
    let mut coherent = vec![0.0; W * H];
    let mut tagged = vec![0.0; W * H];
    for y in 0..H {
        for x in 0..W {
            let (ur, ui) = complex_field(x, y, SLIT_CENTERS[0]);
            let (lr, li) = complex_field(x, y, SLIT_CENTERS[1]);
            coherent[index(x, y)] = (ur + lr).powi(2) + (ui + li).powi(2);
            tagged[index(x, y)] = ur * ur + ui * ui + lr * lr + li * li;
        }
    }
    normalize(&mut coherent);
    normalize(&mut tagged);
    Fields { coherent, tagged }
}

fn normalize(values: &mut [f64]) {
    let maximum = values.iter().copied().fold(0.0_f64, f64::max).max(1.0e-12);
    for value in values {
        *value /= maximum;
    }
}

fn neighbors(cell: usize) -> impl Iterator<Item = usize> {
    let x = cell % W;
    let y = cell / W;
    let mut result = [usize::MAX; 4];
    let mut count = 0;
    if x > 0 {
        result[count] = index(x - 1, y);
        count += 1;
    }
    if x + 1 < W {
        result[count] = index(x + 1, y);
        count += 1;
    }
    if y > 0 {
        result[count] = index(x, y - 1);
        count += 1;
    }
    if y + 1 < H {
        result[count] = index(x, y + 1);
        count += 1;
    }
    result.into_iter().take(count)
}

fn simulate(condition: Condition, seed: u64, fields: &Fields, frames: Option<&Path>) -> ResultRow {
    let mut occupied = vec![false; W * H];
    let mut frontier = HashSet::new();
    let source = index(2, H / 2);
    occupied[source] = true;
    for neighbor in neighbors(source) {
        frontier.insert(neighbor);
    }
    let mut rng = Rng64::new(seed ^ 0x3195_710d_0be5_1a7e);
    let mut connected_step = None;
    if let Some(directory) = frames {
        fs::create_dir_all(directory).unwrap();
        write_pgm(&directory.join("state-0000.pgm"), &occupied).unwrap();
    }

    for step in 0..STEPS {
        let field = if condition.coherent_at(step) {
            &fields.coherent
        } else {
            &fields.tagged
        };
        let mut candidates = Vec::with_capacity(frontier.len());
        let mut total = 0.0;
        let mut frontier_cells: Vec<_> = frontier.iter().copied().collect();
        frontier_cells.sort_unstable();
        for cell in frontier_cells {
            let x = cell % W;
            let y = cell / W;
            if blocked(x, y) {
                continue;
            }
            let occupied_neighbors = neighbors(cell)
                .filter(|neighbor| occupied[*neighbor])
                .count();
            let forward = 0.15 + 2.85 * x as f64 / (W - 1) as f64;
            let wave = 0.003 + field[cell].powf(1.50);
            let weight = wave * forward * (1.0 + 0.18 * occupied_neighbors as f64);
            if weight > 0.0 {
                total += weight;
                candidates.push((cell, weight));
            }
        }
        if total <= 0.0 {
            break;
        }
        let mut draw = rng.unit() * total;
        let mut chosen = candidates.last().unwrap().0;
        for (cell, weight) in candidates {
            if draw <= weight {
                chosen = cell;
                break;
            }
            draw -= weight;
        }
        occupied[chosen] = true;
        frontier.remove(&chosen);
        for neighbor in neighbors(chosen) {
            if !occupied[neighbor] {
                frontier.insert(neighbor);
            }
        }
        if connected_step.is_none() && chosen % W == W - 1 {
            connected_step = Some(step + 1);
        }
        if let Some(directory) = frames {
            if (step + 1) % FRAME_EVERY == 0 || step + 1 == SWITCH_STEP || step + 1 == STEPS {
                write_pgm(
                    &directory.join(format!("state-{:04}.pgm", step + 1)),
                    &occupied,
                )
                .unwrap();
            }
        }
    }

    let occupied_count = occupied.iter().filter(|value| **value).count();
    let coherent_alignment = alignment(&occupied, &fields.coherent);
    let tagged_alignment = alignment(&occupied, &fields.tagged);
    let upper_slit_cells = emitters(SLIT_CENTERS[0])
        .filter(|y| occupied[index(BARRIER_X, *y)])
        .count();
    let lower_slit_cells = emitters(SLIT_CENTERS[1])
        .filter(|y| occupied[index(BARRIER_X, *y)])
        .count();
    ResultRow {
        condition: condition.name(),
        seed,
        connected_step,
        occupied: occupied_count,
        coherent_alignment,
        tagged_alignment,
        upper_slit_cells,
        lower_slit_cells,
    }
}

fn alignment(occupied: &[bool], field: &[f64]) -> f64 {
    let mut sum = 0.0;
    let mut count = 0;
    for y in 0..H {
        for x in (BARRIER_X + 1)..W {
            let cell = index(x, y);
            if occupied[cell] {
                sum += field[cell];
                count += 1;
            }
        }
    }
    if count == 0 { 0.0 } else { sum / count as f64 }
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
    fs::create_dir_all(&output).unwrap();
    let fields = make_fields();
    write_scalar_pgm(&output.join("coherent-field.pgm"), &fields.coherent).unwrap();
    write_scalar_pgm(&output.join("path-tagged-field.pgm"), &fields.tagged).unwrap();
    let conditions = [
        Condition::Coherent,
        Condition::PathTagged,
        Condition::CoherentToTagged,
        Condition::TaggedToCoherent,
    ];
    let mut rows = Vec::new();
    for condition in conditions {
        for offset in 0..ENSEMBLE_SEEDS {
            let seed = 319 + offset as u64;
            let frame_dir = if seed == 319 {
                Some(output.join("frames").join(condition.name()))
            } else {
                None
            };
            rows.push(simulate(condition, seed, &fields, frame_dir.as_deref()));
        }
    }
    let mut writer = BufWriter::new(File::create(output.join("metrics.tsv")).unwrap());
    writeln!(writer, "condition\tseed\tconnected_step\toccupied\tcoherent_alignment\ttagged_alignment\tupper_slit_cells\tlower_slit_cells").unwrap();
    for row in rows {
        let connected = row
            .connected_step
            .map(|value| value.to_string())
            .unwrap_or_else(|| "none".into());
        writeln!(
            writer,
            "{}\t{}\t{}\t{}\t{:.12}\t{:.12}\t{}\t{}",
            row.condition,
            row.seed,
            connected,
            row.occupied,
            row.coherent_alignment,
            row.tagged_alignment,
            row.upper_slit_cells,
            row.lower_slit_cells
        )
        .unwrap();
    }
    println!(
        "output={} conditions=4 seeds={} steps={}",
        output.display(),
        ENSEMBLE_SEEDS,
        STEPS
    );
}

fn write_scalar_pgm(path: &Path, values: &[f64]) -> std::io::Result<()> {
    let mut writer = BufWriter::new(File::create(path)?);
    write!(writer, "P5\n{} {}\n255\n", W, H)?;
    for value in values {
        writer.write_all(&[(value.clamp(0.0, 1.0).sqrt() * 255.0).round() as u8])?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn field_maps_are_normalized_and_distinct() {
        let fields = make_fields();
        assert!((fields.coherent.iter().copied().fold(0.0_f64, f64::max) - 1.0).abs() < 1.0e-12);
        assert!((fields.tagged.iter().copied().fold(0.0_f64, f64::max) - 1.0).abs() < 1.0e-12);
        assert!(
            fields
                .coherent
                .iter()
                .zip(&fields.tagged)
                .any(|(left, right)| (left - right).abs() > 1.0e-6)
        );
    }

    #[test]
    fn barrier_contains_two_exact_apertures() {
        let open: Vec<_> = (0..H).filter(|y| !blocked(BARRIER_X, *y)).collect();
        assert_eq!(open.len(), 2 * (2 * SLIT_HALF_WIDTH + 1));
        assert!(open.contains(&SLIT_CENTERS[0]));
        assert!(open.contains(&SLIT_CENTERS[1]));
    }

    #[test]
    fn switch_histories_change_field_at_the_declared_step() {
        assert!(Condition::CoherentToTagged.coherent_at(SWITCH_STEP - 1));
        assert!(!Condition::CoherentToTagged.coherent_at(SWITCH_STEP));
        assert!(!Condition::TaggedToCoherent.coherent_at(SWITCH_STEP - 1));
        assert!(Condition::TaggedToCoherent.coherent_at(SWITCH_STEP));
    }

    #[test]
    fn seeded_growth_is_deterministic() {
        let fields = make_fields();
        let first = simulate(Condition::Coherent, 319, &fields, None);
        let second = simulate(Condition::Coherent, 319, &fields, None);
        assert_eq!(first.connected_step, second.connected_step);
        assert_eq!(first.occupied, second.occupied);
        assert_eq!(first.coherent_alignment, second.coherent_alignment);
        assert_eq!(first.tagged_alignment, second.tagged_alignment);
    }
}
