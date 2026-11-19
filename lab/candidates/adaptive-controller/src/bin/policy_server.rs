use std::io::{self, BufRead, Write};

use adaptive_controller_candidate::{Controller, ControllerConfig, parse_observation_strict};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();
    let config_line = lines.next().ok_or("missing controller configuration")??;
    let config: ControllerConfig = serde_json::from_str(&config_line)?;
    let mut controller = Controller::new(config)
        .map_err(|error| format!("invalid controller configuration: {error:?}"))?;
    let stdout = io::stdout();
    let mut output = stdout.lock();

    for line in lines {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let observation = parse_observation_strict(&line)
            .map_err(|error| format!("invalid observation: {error:?}"))?;
        let audit = controller.step(&observation);
        writeln!(output, "{}", audit.canonical_json()?)?;
        output.flush()?;
    }
    Ok(())
}
