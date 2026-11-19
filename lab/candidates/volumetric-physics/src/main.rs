use std::cmp::Ordering;
use std::env;
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::{Path, PathBuf};

const DIRS: [(isize, isize, isize); 6] = [
    (-1, 0, 0),
    (1, 0, 0),
    (0, -1, 0),
    (0, 1, 0),
    (0, 0, -1),
    (0, 0, 1),
];

#[derive(Clone, Copy, Debug)]
struct SolveStats {
    iterations: usize,
    residual_linf: f64,
    residual_l2: f64,
    converged: bool,
}

#[derive(Clone, Copy, Debug)]
struct FieldStats {
    source_current: f64,
    sink_current: f64,
    joule_power: f64,
    max_current: f64,
}

#[derive(Clone, Copy, Debug)]
struct GrowthStats {
    added: usize,
    out_of_plane: usize,
    plus_z: usize,
    minus_z: usize,
}

#[derive(Clone, Copy, Debug)]
struct Candidate {
    index: usize,
    direction: [i8; 3],
    key: f64,
}

struct Grid {
    nx: usize,
    ny: usize,
    nz: usize,
    spacing: f64,
    sigma_medium: f64,
    sigma_material: f64,
    occupied: Vec<bool>,
    voltage: Vec<f64>,
    growth_epoch: Vec<i32>,
    growth_direction: Vec<[i8; 3]>,
}

impl Grid {
    fn new(nx: usize, ny: usize, nz: usize, sigma_medium: f64, sigma_material: f64) -> Self {
        let count = nx * ny * nz;
        let spacing = 1.0 / (nx.saturating_sub(1).max(1) as f64);
        let mut voltage = vec![0.0; count];
        for z in 0..nz {
            for y in 0..ny {
                for x in 0..nx {
                    let index = (z * ny + y) * nx + x;
                    voltage[index] = 1.0 - x as f64 / (nx - 1) as f64;
                }
            }
        }
        Self {
            nx,
            ny,
            nz,
            spacing,
            sigma_medium,
            sigma_material,
            occupied: vec![false; count],
            voltage,
            growth_epoch: vec![-1; count],
            growth_direction: vec![[0, 0, 0]; count],
        }
    }

    #[inline]
    fn idx(&self, x: usize, y: usize, z: usize) -> usize {
        (z * self.ny + y) * self.nx + x
    }

    #[inline]
    fn neighbor(
        &self,
        x: usize,
        y: usize,
        z: usize,
        direction: (isize, isize, isize),
    ) -> Option<(usize, usize, usize)> {
        let xn = x as isize + direction.0;
        let yn = y as isize + direction.1;
        let zn = z as isize + direction.2;
        if xn < 0
            || yn < 0
            || zn < 0
            || xn >= self.nx as isize
            || yn >= self.ny as isize
            || zn >= self.nz as isize
        {
            None
        } else {
            Some((xn as usize, yn as usize, zn as usize))
        }
    }

    #[inline]
    fn conductivity(&self, index: usize) -> f64 {
        if self.occupied[index] {
            self.sigma_material
        } else {
            self.sigma_medium
        }
    }

    #[inline]
    fn harmonic(a: f64, b: f64) -> f64 {
        2.0 * a * b / (a + b)
    }

    fn seed_layer(&mut self, seed_path: &Path) -> Result<usize, Box<dyn Error>> {
        let file = BufReader::new(File::open(seed_path)?);
        let z = self.nz / 2;
        let mut count = 0usize;
        for line in file.lines() {
            let line = line?;
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with('x') {
                continue;
            }
            let mut fields = trimmed.split_whitespace();
            let x: usize = fields.next().ok_or("seed row lacks x")?.parse()?;
            let y: usize = fields.next().ok_or("seed row lacks y")?.parse()?;
            if fields.next().is_some() {
                return Err(format!("seed row has extra fields: {trimmed}").into());
            }
            if x >= self.nx || y >= self.ny {
                return Err(format!("seed coordinate outside grid: {x},{y}").into());
            }
            let index = self.idx(x, y, z);
            if !self.occupied[index] {
                self.occupied[index] = true;
                self.growth_epoch[index] = 0;
                count += 1;
            }
        }
        Ok(count)
    }

    fn face_coefficient(&self, a: usize, b: usize) -> f64 {
        Self::harmonic(self.conductivity(a), self.conductivity(b)) / (self.spacing * self.spacing)
    }

    fn residual(&self) -> (f64, f64) {
        let mut linf = 0.0f64;
        let mut sum_squared = 0.0f64;
        let mut count = 0usize;
        for z in 0..self.nz {
            for y in 0..self.ny {
                for x in 1..self.nx - 1 {
                    let index = self.idx(x, y, z);
                    let mut balance = 0.0;
                    let mut diagonal = 0.0;
                    for direction in DIRS {
                        if let Some((xn, yn, zn)) = self.neighbor(x, y, z, direction) {
                            let other = self.idx(xn, yn, zn);
                            let coefficient = self.face_coefficient(index, other);
                            balance += coefficient * (self.voltage[other] - self.voltage[index]);
                            diagonal += coefficient;
                        }
                    }
                    let normalized = balance.abs() / diagonal.max(f64::MIN_POSITIVE);
                    linf = linf.max(normalized);
                    sum_squared += normalized * normalized;
                    count += 1;
                }
            }
        }
        (linf, (sum_squared / count.max(1) as f64).sqrt())
    }

    fn solve(&mut self, tolerance: f64, max_iterations: usize, omega: f64) -> SolveStats {
        for z in 0..self.nz {
            for y in 0..self.ny {
                let source = self.idx(0, y, z);
                let sink = self.idx(self.nx - 1, y, z);
                self.voltage[source] = 1.0;
                self.voltage[sink] = 0.0;
            }
        }

        for iteration in 1..=max_iterations {
            for parity in 0..2 {
                for z in 0..self.nz {
                    for y in 0..self.ny {
                        for x in 1..self.nx - 1 {
                            if (x + y + z) & 1 != parity {
                                continue;
                            }
                            let index = self.idx(x, y, z);
                            let mut weighted_neighbors = 0.0;
                            let mut diagonal = 0.0;
                            for direction in DIRS {
                                if let Some((xn, yn, zn)) = self.neighbor(x, y, z, direction) {
                                    let other = self.idx(xn, yn, zn);
                                    let coefficient = self.face_coefficient(index, other);
                                    weighted_neighbors += coefficient * self.voltage[other];
                                    diagonal += coefficient;
                                }
                            }
                            let target = weighted_neighbors / diagonal.max(f64::MIN_POSITIVE);
                            self.voltage[index] =
                                (1.0 - omega) * self.voltage[index] + omega * target;
                        }
                    }
                }
            }
            if iteration == 1 || iteration % 10 == 0 {
                let current = self.residual();
                if current.0 <= tolerance {
                    return SolveStats {
                        iterations: iteration,
                        residual_linf: current.0,
                        residual_l2: current.1,
                        converged: true,
                    };
                }
            }
        }
        let last = self.residual();
        SolveStats {
            iterations: max_iterations,
            residual_linf: last.0,
            residual_l2: last.1,
            converged: last.0 <= tolerance,
        }
    }

    fn face_flux_between(&self, a: usize, b: usize) -> f64 {
        Self::harmonic(self.conductivity(a), self.conductivity(b))
            * (self.voltage[a] - self.voltage[b]).abs()
            / self.spacing
    }

    fn current_vectors_and_joule(&self) -> (Vec<[f32; 3]>, Vec<f32>, FieldStats) {
        let count = self.nx * self.ny * self.nz;
        let mut current = vec![[0.0f32; 3]; count];
        let mut joule_power_by_cell = vec![0.0f64; count];
        let mut max_current = 0.0f64;
        let mut joule_power = 0.0f64;

        for z in 0..self.nz {
            for y in 0..self.ny {
                for x in 0..self.nx {
                    let index = self.idx(x, y, z);
                    let component = |negative: Option<(usize, usize, usize)>,
                                     positive: Option<(usize, usize, usize)>|
                     -> f64 {
                        let mut total = 0.0;
                        let mut faces = 0.0f64;
                        if let Some((xn, yn, zn)) = negative {
                            let other = self.idx(xn, yn, zn);
                            let k =
                                Self::harmonic(self.conductivity(index), self.conductivity(other));
                            total +=
                                -k * (self.voltage[index] - self.voltage[other]) / self.spacing;
                            faces += 1.0;
                        }
                        if let Some((xp, yp, zp)) = positive {
                            let other = self.idx(xp, yp, zp);
                            let k =
                                Self::harmonic(self.conductivity(index), self.conductivity(other));
                            total +=
                                -k * (self.voltage[other] - self.voltage[index]) / self.spacing;
                            faces += 1.0;
                        }
                        total / faces.max(1.0)
                    };
                    let jx = component(
                        self.neighbor(x, y, z, (-1, 0, 0)),
                        self.neighbor(x, y, z, (1, 0, 0)),
                    );
                    let jy = component(
                        self.neighbor(x, y, z, (0, -1, 0)),
                        self.neighbor(x, y, z, (0, 1, 0)),
                    );
                    let jz = component(
                        self.neighbor(x, y, z, (0, 0, -1)),
                        self.neighbor(x, y, z, (0, 0, 1)),
                    );
                    let magnitude = (jx * jx + jy * jy + jz * jz).sqrt();
                    current[index] = [jx as f32, jy as f32, jz as f32];
                    max_current = max_current.max(magnitude);
                }
            }
        }

        // Discrete face power is k_face * (delta V)^2 * area / distance.
        // Each unique face contributes half to each neighboring cell so the
        // written cell density integrates exactly to the finite-volume power.
        let cell_volume = self.spacing.powi(3);
        for z in 0..self.nz {
            for y in 0..self.ny {
                for x in 0..self.nx {
                    let index = self.idx(x, y, z);
                    for direction in [(1, 0, 0), (0, 1, 0), (0, 0, 1)] {
                        if let Some((xn, yn, zn)) = self.neighbor(x, y, z, direction) {
                            let other = self.idx(xn, yn, zn);
                            let k =
                                Self::harmonic(self.conductivity(index), self.conductivity(other));
                            let delta = self.voltage[index] - self.voltage[other];
                            let power = k * delta * delta * self.spacing;
                            joule_power_by_cell[index] += 0.5 * power;
                            joule_power_by_cell[other] += 0.5 * power;
                            joule_power += power;
                        }
                    }
                }
            }
        }
        let joule = joule_power_by_cell
            .into_iter()
            .map(|power| (power / cell_volume) as f32)
            .collect::<Vec<_>>();

        let face_area = self.spacing * self.spacing;
        let mut source_current = 0.0;
        let mut sink_current = 0.0;
        for z in 0..self.nz {
            for y in 0..self.ny {
                let source = self.idx(0, y, z);
                let source_inside = self.idx(1, y, z);
                source_current +=
                    Self::harmonic(self.conductivity(source), self.conductivity(source_inside))
                        * (self.voltage[source] - self.voltage[source_inside])
                        / self.spacing
                        * face_area;

                let sink_inside = self.idx(self.nx - 2, y, z);
                let sink = self.idx(self.nx - 1, y, z);
                sink_current +=
                    Self::harmonic(self.conductivity(sink_inside), self.conductivity(sink))
                        * (self.voltage[sink_inside] - self.voltage[sink])
                        / self.spacing
                        * face_area;
            }
        }

        (
            current,
            joule,
            FieldStats {
                source_current,
                sink_current,
                joule_power,
                max_current,
            },
        )
    }

    fn grow_six_neighbor(
        &mut self,
        epoch: i32,
        requested: usize,
        rng: &mut SplitMix64,
    ) -> GrowthStats {
        let mut candidates = Vec::new();
        for z in 0..self.nz {
            for y in 0..self.ny {
                for x in 1..self.nx - 1 {
                    let index = self.idx(x, y, z);
                    if self.occupied[index] {
                        continue;
                    }
                    let mut best_flux = 0.0f64;
                    let mut best_direction = [0i8; 3];
                    for direction in DIRS {
                        if let Some((xn, yn, zn)) = self.neighbor(x, y, z, direction) {
                            let other = self.idx(xn, yn, zn);
                            if self.occupied[other] {
                                let flux = self.face_flux_between(index, other);
                                if flux > best_flux {
                                    best_flux = flux;
                                    best_direction = [
                                        -direction.0 as i8,
                                        -direction.1 as i8,
                                        -direction.2 as i8,
                                    ];
                                }
                            }
                        }
                    }
                    if best_flux > 0.0 {
                        let u = rng.next_f64().max(f64::MIN_POSITIVE);
                        let key = -u.ln() / best_flux.max(1.0e-18);
                        candidates.push(Candidate {
                            index,
                            direction: best_direction,
                            key,
                        });
                    }
                }
            }
        }
        candidates.sort_unstable_by(|a, b| a.key.partial_cmp(&b.key).unwrap_or(Ordering::Equal));

        let mut stats = GrowthStats {
            added: 0,
            out_of_plane: 0,
            plus_z: 0,
            minus_z: 0,
        };
        for candidate in candidates.into_iter().take(requested) {
            self.occupied[candidate.index] = true;
            self.growth_epoch[candidate.index] = epoch;
            self.growth_direction[candidate.index] = candidate.direction;
            stats.added += 1;
            if candidate.direction[2] != 0 {
                stats.out_of_plane += 1;
                if candidate.direction[2] > 0 {
                    stats.plus_z += 1;
                } else {
                    stats.minus_z += 1;
                }
            }
        }
        stats
    }

    fn occupied_count(&self) -> usize {
        self.occupied.iter().filter(|value| **value).count()
    }

    fn write_vtk(
        &self,
        path: &Path,
        current: &[[f32; 3]],
        joule: &[f32],
    ) -> Result<(), Box<dyn Error>> {
        let mut writer = BufWriter::new(File::create(path)?);
        let count = self.nx * self.ny * self.nz;
        writeln!(writer, "# vtk DataFile Version 3.0")?;
        writeln!(
            writer,
            "SIMULATED 3D PHYSICS: six-neighbor conductive volume"
        )?;
        writeln!(writer, "BINARY")?;
        writeln!(writer, "DATASET STRUCTURED_POINTS")?;
        writeln!(writer, "DIMENSIONS {} {} {}", self.nx, self.ny, self.nz)?;
        writeln!(writer, "ORIGIN 0 0 0")?;
        writeln!(
            writer,
            "SPACING {:.17} {:.17} {:.17}",
            self.spacing, self.spacing, self.spacing
        )?;
        writeln!(writer, "POINT_DATA {count}")?;

        writeln!(writer, "SCALARS occupancy unsigned_char 1")?;
        writeln!(writer, "LOOKUP_TABLE default")?;
        for occupied in &self.occupied {
            writer.write_all(&[u8::from(*occupied)])?;
        }
        writer.write_all(b"\n")?;

        write_f32_scalar(
            &mut writer,
            "conductivity",
            &(0..count)
                .map(|i| self.conductivity(i) as f32)
                .collect::<Vec<_>>(),
        )?;
        write_f32_scalar(
            &mut writer,
            "voltage",
            &self.voltage.iter().map(|v| *v as f32).collect::<Vec<_>>(),
        )?;
        write_f32_scalar(
            &mut writer,
            "current_magnitude",
            &current
                .iter()
                .map(|v| (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt())
                .collect::<Vec<_>>(),
        )?;
        write_f32_scalar(&mut writer, "joule_density", joule)?;

        writeln!(writer, "SCALARS growth_epoch int 1")?;
        writeln!(writer, "LOOKUP_TABLE default")?;
        for value in &self.growth_epoch {
            writer.write_all(&value.to_be_bytes())?;
        }
        writer.write_all(b"\n")?;

        writeln!(writer, "VECTORS current float")?;
        for vector in current {
            for value in vector {
                writer.write_all(&value.to_be_bytes())?;
            }
        }
        writer.write_all(b"\n")?;

        writeln!(writer, "VECTORS growth_direction float")?;
        for vector in &self.growth_direction {
            for value in vector {
                writer.write_all(&(*value as f32).to_be_bytes())?;
            }
        }
        writer.write_all(b"\n")?;
        writer.flush()?;
        Ok(())
    }
}

fn write_f32_scalar(
    writer: &mut BufWriter<File>,
    name: &str,
    values: &[f32],
) -> Result<(), Box<dyn Error>> {
    writeln!(writer, "SCALARS {name} float 1")?;
    writeln!(writer, "LOOKUP_TABLE default")?;
    for value in values {
        writer.write_all(&value.to_be_bytes())?;
    }
    writer.write_all(b"\n")?;
    Ok(())
}

struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }

    fn next_f64(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64) * (1.0 / ((1u64 << 53) as f64))
    }
}

fn run_convergence_test() -> Result<(), Box<dyn Error>> {
    let mut grid = Grid::new(18, 12, 7, 1.0, 1.0);
    for z in 0..grid.nz {
        for y in 0..grid.ny {
            for x in 1..grid.nx - 1 {
                let index = grid.idx(x, y, z);
                grid.voltage[index] = 0.17 + 0.31 * ((x + 3 * y + 7 * z) % 11) as f64 / 10.0;
            }
        }
    }
    let initial_residual = grid.residual().0;
    let solve = grid.solve(1.0e-9, 4000, 1.65);
    if !solve.converged {
        return Err(format!("convergence test did not converge: {solve:?}").into());
    }
    let mut analytic_error = 0.0f64;
    for z in 0..grid.nz {
        for y in 0..grid.ny {
            for x in 0..grid.nx {
                let exact = 1.0 - x as f64 / (grid.nx - 1) as f64;
                analytic_error =
                    analytic_error.max((grid.voltage[grid.idx(x, y, z)] - exact).abs());
            }
        }
    }
    let (_, _, fields) = grid.current_vectors_and_joule();
    let conservation = (fields.source_current - fields.sink_current).abs()
        / fields.source_current.abs().max(1.0e-15);
    if analytic_error > 2.0e-7 || conservation > 2.0e-7 || solve.residual_linf >= initial_residual {
        return Err(format!(
            "convergence bounds failed: error={analytic_error:e} conservation={conservation:e}"
        )
        .into());
    }
    println!(
        "PASS convergence-test grid=18x12x7 iterations={} residual_initial={:.6e} residual_final={:.6e} analytic_max_error={:.6e} source_sink_relative_error={:.6e}",
        solve.iterations, initial_residual, solve.residual_linf, analytic_error, conservation
    );
    Ok(())
}

fn run_simulation(seed_path: &Path, output_dir: &Path) -> Result<(), Box<dyn Error>> {
    fs::create_dir_all(output_dir)?;
    let mut grid = Grid::new(192, 128, 9, 0.01, 1.0);
    let initial_occupied = grid.seed_layer(seed_path)?;
    if initial_occupied == 0 {
        return Err("seed contains no occupied cells".into());
    }

    let metrics_path = output_dir.join("metrics.tsv");
    let mut metrics = BufWriter::new(File::create(&metrics_path)?);
    writeln!(
        metrics,
        "epoch\toccupied_voxels\tnew_voxels\tout_of_plane_new\tplus_z_new\tminus_z_new\tmaterial_volume\tsource_current\tsink_current\tjoule_power\tmax_current\titerations\tresidual_linf\tresidual_l2"
    )?;

    let mut rng = SplitMix64::new(319);
    let mut last_growth = GrowthStats {
        added: 0,
        out_of_plane: 0,
        plus_z: 0,
        minus_z: 0,
    };
    let evolution_steps = 3i32;
    let mut total_out_of_plane = 0usize;
    let mut final_solve = SolveStats {
        iterations: 0,
        residual_linf: f64::INFINITY,
        residual_l2: f64::INFINITY,
        converged: false,
    };
    let mut final_fields = FieldStats {
        source_current: 0.0,
        sink_current: 0.0,
        joule_power: 0.0,
        max_current: 0.0,
    };
    let mut final_current = Vec::new();
    let mut final_joule = Vec::new();

    for epoch in 0..=evolution_steps {
        let solve = grid.solve(5.0e-8, 12000, 1.55);
        if !solve.converged {
            return Err(format!("epoch {epoch} solver did not converge: {solve:?}").into());
        }
        let (current, joule, fields) = grid.current_vectors_and_joule();
        let material_volume = grid.occupied_count() as f64 * grid.spacing.powi(3);
        writeln!(
            metrics,
            "{}\t{}\t{}\t{}\t{}\t{}\t{:.12e}\t{:.12e}\t{:.12e}\t{:.12e}\t{:.12e}\t{}\t{:.12e}\t{:.12e}",
            epoch,
            grid.occupied_count(),
            last_growth.added,
            last_growth.out_of_plane,
            last_growth.plus_z,
            last_growth.minus_z,
            material_volume,
            fields.source_current,
            fields.sink_current,
            fields.joule_power,
            fields.max_current,
            solve.iterations,
            solve.residual_linf,
            solve.residual_l2,
        )?;
        println!(
            "epoch={epoch}/{evolution_steps} occupied={} sink_current={:.6e} residual={:.3e} out_of_plane_new={}",
            grid.occupied_count(),
            fields.sink_current,
            solve.residual_linf,
            last_growth.out_of_plane
        );
        final_solve = solve;
        final_fields = fields;
        final_current = current;
        final_joule = joule;
        if epoch < evolution_steps {
            last_growth = grid.grow_six_neighbor(epoch + 1, 160, &mut rng);
            total_out_of_plane += last_growth.out_of_plane;
        }
    }
    metrics.flush()?;

    if total_out_of_plane == 0 {
        return Err("six-neighbor evolution made no out-of-plane choices".into());
    }
    let vtk_path = output_dir.join("final-volume.vtk");
    grid.write_vtk(&vtk_path, &final_current, &final_joule)?;

    let conservation = (final_fields.source_current - final_fields.sink_current).abs()
        / final_fields.source_current.abs().max(1.0e-15);
    let energy_balance = (final_fields.source_current - final_fields.joule_power).abs()
        / final_fields.source_current.abs().max(1.0e-15);
    if conservation > 2.0e-3 || energy_balance > 2.0e-3 {
        return Err(format!(
            "final conservation gate failed: source_sink={conservation:e} source_joule={energy_balance:e}"
        )
        .into());
    }
    let summary_path = output_dir.join("summary.json");
    let mut summary = BufWriter::new(File::create(&summary_path)?);
    writeln!(summary, "{{")?;
    writeln!(summary, "  \"schema\": \"volumetric-physics-result/v1\",")?;
    writeln!(summary, "  \"label\": \"SIMULATED 3D PHYSICS\",")?;
    writeln!(summary, "  \"grid\": [192, 128, 9],")?;
    writeln!(
        summary,
        "  \"initial_condition\": \"Exact 192 by 128 occupied-cell skeleton placed only on z=4\","
    )?;
    writeln!(summary, "  \"neighbor_rule\": \"six face-neighbors only\",")?;
    writeln!(
        summary,
        "  \"boundary_conditions\": \"V=1 at x=0, V=0 at x=191, zero normal flux on y and z exterior faces\","
    )?;
    writeln!(summary, "  \"conductivity_material\": 1.0,")?;
    writeln!(summary, "  \"conductivity_medium\": 0.01,")?;
    writeln!(
        summary,
        "  \"initial_occupied_voxels\": {initial_occupied},"
    )?;
    writeln!(
        summary,
        "  \"final_occupied_voxels\": {},",
        grid.occupied_count()
    )?;
    writeln!(
        summary,
        "  \"out_of_plane_growth_choices\": {total_out_of_plane},"
    )?;
    writeln!(
        summary,
        "  \"final_sink_current\": {:.12e},",
        final_fields.sink_current
    )?;
    writeln!(
        summary,
        "  \"final_joule_power\": {:.12e},",
        final_fields.joule_power
    )?;
    writeln!(
        summary,
        "  \"final_max_current\": {:.12e},",
        final_fields.max_current
    )?;
    writeln!(
        summary,
        "  \"solver_iterations\": {},",
        final_solve.iterations
    )?;
    writeln!(
        summary,
        "  \"solver_residual_linf\": {:.12e},",
        final_solve.residual_linf
    )?;
    writeln!(
        summary,
        "  \"solver_residual_l2\": {:.12e},",
        final_solve.residual_l2
    )?;
    writeln!(
        summary,
        "  \"source_sink_relative_error\": {:.12e},",
        conservation
    )?;
    writeln!(
        summary,
        "  \"source_joule_relative_error\": {:.12e},",
        energy_balance
    )?;
    writeln!(
        summary,
        "  \"unit_boundary\": \"Dimensionless computational mechanism test; no physical material calibration is claimed.\""
    )?;
    writeln!(summary, "}}")?;
    summary.flush()?;

    println!(
        "PASS SIMULATED 3D PHYSICS vtk={} metrics={} summary={} out_of_plane_choices={}",
        vtk_path.display(),
        metrics_path.display(),
        summary_path.display(),
        total_out_of_plane
    );
    Ok(())
}

fn usage(program: &str) {
    eprintln!(
        "usage:\n  {program} --convergence-test\n  {program} --simulate SEED_CELLS_TSV OUTPUT_DIR"
    );
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    match args.as_slice() {
        [_, flag] if flag == "--convergence-test" => run_convergence_test(),
        [_, flag, seed, output] if flag == "--simulate" => {
            run_simulation(&PathBuf::from(seed), &PathBuf::from(output))
        }
        _ => {
            usage(
                args.first()
                    .map(String::as_str)
                    .unwrap_or("volumetric-physics"),
            );
            Err("invalid arguments".into())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn harmonic_face_conductivity_is_symmetric() {
        let a = Grid::harmonic(0.01, 1.0);
        let b = Grid::harmonic(1.0, 0.01);
        assert!((a - b).abs() < f64::EPSILON);
        assert!(a > 0.01 && a < 1.0);
    }

    #[test]
    fn interior_voxel_has_six_neighbors() {
        let grid = Grid::new(5, 5, 5, 0.01, 1.0);
        let count = DIRS
            .iter()
            .filter(|direction| grid.neighbor(2, 2, 2, **direction).is_some())
            .count();
        assert_eq!(count, 6);
    }

    #[test]
    fn corner_has_three_neighbors() {
        let grid = Grid::new(5, 5, 5, 0.01, 1.0);
        let count = DIRS
            .iter()
            .filter(|direction| grid.neighbor(0, 0, 0, **direction).is_some())
            .count();
        assert_eq!(count, 3);
    }
}
