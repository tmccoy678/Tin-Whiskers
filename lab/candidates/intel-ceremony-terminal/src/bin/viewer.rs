use std::collections::{HashSet, VecDeque, hash_map::DefaultHasher};
use std::env;
use std::fs;
use std::hash::{Hash, Hasher};
use std::io::{self, Write};
use std::path::PathBuf;
use std::thread;
use std::time::{Duration, Instant};

const WIDTH: usize = 80;
const HEIGHT: usize = 24;
const MAX_PENDING: usize = 8;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let source = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/Users/agar/.blu-ephemeral/current.ansi"));
    let delay_ms: u64 = env::args()
        .nth(2)
        .unwrap_or_else(|| "1000".into())
        .parse()?;
    let queue_dir = source
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."))
        .join("queue");
    fs::create_dir_all(&queue_dir)?;
    let mut displayed_hash = 0_u64;
    let mut pending: VecDeque<(Instant, u64, String)> = VecDeque::new();
    let mut pending_hashes = HashSet::new();

    loop {
        let mut queued_paths: Vec<_> = fs::read_dir(&queue_dir)?
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| path.extension().and_then(|value| value.to_str()) == Some("ansi"))
            .collect();
        queued_paths.sort();
        for path in queued_paths
            .into_iter()
            .take(MAX_PENDING.saturating_sub(pending.len()))
        {
            if let Ok(bytes) = fs::read(&path) {
                let hash = hash64(&bytes);
                if hash != displayed_hash && !pending_hashes.contains(&hash) {
                    let text = String::from_utf8_lossy(&bytes).into_owned();
                    pending.push_back((
                        Instant::now() + Duration::from_millis(delay_ms),
                        hash,
                        text,
                    ));
                    pending_hashes.insert(hash);
                }
                fs::remove_file(path)?;
            }
        }

        if pending.is_empty() && displayed_hash == 0 {
            if let Ok(bytes) = fs::read(&source) {
                let hash = hash64(&bytes);
                pending.push_back((
                    Instant::now() + Duration::from_millis(delay_ms),
                    hash,
                    String::from_utf8_lossy(&bytes).into_owned(),
                ));
                pending_hashes.insert(hash);
            }
        }

        if pending
            .front()
            .is_some_and(|value| Instant::now() >= value.0)
        {
            let (_, hash, text) = pending.pop_front().unwrap();
            pending_hashes.remove(&hash);
            draw(&text, hash, delay_ms, pending.len())?;
            displayed_hash = hash;
        }
        thread::sleep(Duration::from_millis(100));
    }
}

fn hash64(bytes: &[u8]) -> u64 {
    let mut hasher = DefaultHasher::new();
    bytes.hash(&mut hasher);
    hasher.finish()
}

fn draw(text: &str, hash: u64, delay_ms: u64, pending: usize) -> io::Result<()> {
    let mut output = io::stdout().lock();
    write!(output, "\x1b[2J\x1b[H\x1b[32m")?;
    writeln!(output, "+{}+", "-".repeat(WIDTH - 2))?;
    line(
        &mut output,
        "BLU COMPUTE CEREMONY",
        Some("WIRED / ATOMIC / RUST"),
    )?;
    line(
        &mut output,
        &format!("DELAY {:>6} ms", delay_ms),
        Some(&format!(
            "QUEUE {:>3} / {}  SOURCE {:016x}",
            pending, MAX_PENDING, hash
        )),
    )?;
    writeln!(output, "+{}+", "-".repeat(WIDTH - 2))?;

    let body_lines = HEIGHT - 6;
    for value in text.lines().take(body_lines) {
        line(&mut output, value, None)?;
    }
    for _ in text.lines().take(body_lines).count()..body_lines {
        line(&mut output, "", None)?;
    }
    writeln!(output, "+{}+\x1b[0m", "-".repeat(WIDTH - 2))?;
    output.flush()
}

fn line(output: &mut impl Write, left: &str, right: Option<&str>) -> io::Result<()> {
    let inner = WIDTH - 4;
    let left_width = left.chars().count();
    let mut content = match right {
        Some(right) if left_width + right.chars().count() + 1 <= inner => {
            format!(
                "{}{}{}",
                left,
                " ".repeat(inner - left_width - right.chars().count()),
                right
            )
        }
        _ => left.to_string(),
    };
    if content.chars().count() > inner {
        content = content.chars().take(inner).collect();
    }
    writeln!(output, "| {:inner$} |", content)
}
