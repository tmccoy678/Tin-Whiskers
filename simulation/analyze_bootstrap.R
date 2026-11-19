args <- commandArgs(trailingOnly = TRUE)
input <- if (length(args) >= 1) args[[1]] else "simulation/results/paired-seed-1-128.tsv"
summary_path <- if (length(args) >= 2) args[[2]] else "simulation/results/paired-seed-1-128-summary.md"
figure_path <- if (length(args) >= 3) args[[3]] else "figures/cherenkov-bootstrap-paired.png"

raw <- read.delim(input, sep = "\t", quote = "", stringsAsFactors = FALSE)
number <- function(key, x) as.numeric(sub(paste0(".*", key, "=([0-9.]+).*"), "\\1", x))
logical_value <- function(key, x) sub(paste0(".*", key, "=([^ ]+).*"), "\\1", x) == "true"

raw$steps <- number("steps_completed", raw$result)
raw$metal <- number("metal", raw$result)
raw$bridged <- logical_value("bridged", raw$result)

baseline <- raw[raw$condition == "baseline", c("seed", "steps", "metal", "bridged")]
cherenkov <- raw[raw$condition == "cherenkov", c("seed", "steps", "metal", "bridged")]
names(baseline)[-1] <- paste0(names(baseline)[-1], "_baseline")
names(cherenkov)[-1] <- paste0(names(cherenkov)[-1], "_cherenkov")
d <- merge(baseline, cherenkov, by = "seed", sort = TRUE)

d$step_gain <- d$steps_baseline - d$steps_cherenkov
d$cell_gain <- d$metal_baseline - d$metal_cherenkov

set.seed(319)
bootstrap_ci <- function(x, b = 10000) {
  estimates <- replicate(b, mean(sample(x, length(x), replace = TRUE)))
  unname(quantile(estimates, c(0.025, 0.975)))
}

step_ci <- bootstrap_ci(d$step_gain)
cell_ci <- bootstrap_ci(d$cell_gain)

power_at_n <- function(x, n, repetitions = 3000) {
  mean(replicate(repetitions, {
    sample_x <- sample(x, n, replace = TRUE)
    if (sd(sample_x) == 0) return(mean(sample_x) != 0)
    t.test(sample_x, mu = 0, alternative = "two.sided")$p.value < 0.05
  }))
}

candidate_n <- 3:min(128, nrow(d))
power_curve <- vapply(candidate_n, function(n) power_at_n(d$step_gain, n), numeric(1))
n80 <- candidate_n[which(power_curve >= 0.80)[1]]
n90 <- candidate_n[which(power_curve >= 0.90)[1]]

fmt <- function(x, digits = 2) formatC(x, digits = digits, format = "f")
lines <- c(
  "# Paired Cherenkov bootstrap",
  "",
  sprintf("- Paired seeds: **%d** (`1` through `%d`).", nrow(d), max(d$seed)),
  sprintf("- Baseline bridge success: **%d/%d**.", sum(d$bridged_baseline), nrow(d)),
  sprintf("- Cherenkov bridge success: **%d/%d**.", sum(d$bridged_cherenkov), nrow(d)),
  sprintf("- Mean step gain (baseline minus Cherenkov): **%s steps**; 95%% paired-bootstrap CI **[%s, %s]**.", fmt(mean(d$step_gain)), fmt(step_ci[1]), fmt(step_ci[2])),
  sprintf("- Cherenkov bridged earlier in **%d/%d** paired seeds.", sum(d$step_gain > 0), nrow(d)),
  sprintf("- Mean occupied-cell gain: **%s cells**; 95%% paired-bootstrap CI **[%s, %s]**.", fmt(mean(d$cell_gain)), fmt(cell_ci[1]), fmt(cell_ci[2])),
  sprintf("- Cherenkov used fewer occupied cells in **%d/%d** paired seeds.", sum(d$cell_gain > 0), nrow(d)),
  sprintf("- Bootstrap power estimate for the primary step endpoint: **n = %d** paired units for 80%% power and **n = %d** for 90%% power at two-sided alpha = 0.05.", n80, n90),
  "",
  "The power estimate describes variance across simulated microstate seeds. A physical pilot replaces that variance estimate with dish-to-dish variance before fixing the material sample size.",
  "",
  "## Decision rule",
  "",
  "The Cherenkov condition supports the directional hypothesis when the paired-bootstrap confidence interval for baseline-minus-Cherenkov bridge steps lies entirely above zero. An interval containing zero retains the null. An interval entirely below zero reverses the hypothesized direction."
)
writeLines(lines, summary_path)

png(figure_path, width = 1600, height = 980, res = 160, type = "quartz", bg = "#05070B")
par(
  mfrow = c(1, 2), mar = c(5, 5, 3, 1.5), oma = c(0, 0, 2.5, 0),
  bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF"
)
hist(d$step_gain, breaks = 24, col = "#48BDF0", border = "#BDEBFF",
     main = "Bridge-step gain", xlab = "baseline steps minus Cherenkov steps",
     col.main = "#FFFFFF")
abline(v = 0, col = "#FF7B7B", lwd = 3)
hist(d$cell_gain, breaks = 24, col = "#B9F2D0", border = "#E7FFF1",
     main = "Occupied-cell gain", xlab = "baseline cells minus Cherenkov cells",
     col.main = "#FFFFFF")
abline(v = 0, col = "#FF7B7B", lwd = 3)
mtext("Paired Cherenkov condition · simulated seeds", outer = TRUE, side = 3,
      line = 0.5, col = "#FFFFFF", cex = 1.4, font = 2)
dev.off()

cat(paste(lines, collapse = "\n"), "\n")
