use std::env;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let source = env::args()
        .nth(1)
        .map(PathBuf::from)
        .ok_or("source path required")?;
    let host = env::args().nth(2).unwrap_or_else(|| "blu-intel-lan".into());
    let poll_ms: u64 = env::args().nth(3).unwrap_or_else(|| "250".into()).parse()?;
    let mut last_sent = Vec::new();
    let mut sequence = 0_u64;

    loop {
        if let Ok(bytes) = fs::read(&source) {
            if bytes != last_sent {
                publish(&host, sequence, &bytes)?;
                sequence = sequence.wrapping_add(1);
                last_sent = bytes;
            }
        }
        thread::sleep(Duration::from_millis(poll_ms));
    }
}

fn publish(host: &str, sequence: u64, bytes: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    let remote = format!(
        "umask 077; d=/Users/agar/.blu-ephemeral; q=\"$d/queue\"; mkdir -p \"$q\"; t=\"$q/.tmp.$$\"; c=\"$d/.current.$$\"; cat >\"$t\" && cp \"$t\" \"$c\" && mv -f \"$t\" \"$q/{sequence:020}.ansi\" && mv -f \"$c\" \"$d/current.ansi\""
    );
    let mut child = Command::new("ssh")
        .args(["-o", "BatchMode=yes", host, &remote])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()?;
    child
        .stdin
        .as_mut()
        .ok_or("ssh stdin unavailable")?
        .write_all(bytes)?;
    let status = child.wait()?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("ssh publish exited {status}").into())
    }
}
