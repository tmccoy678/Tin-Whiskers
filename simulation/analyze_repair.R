args <- commandArgs(trailingOnly = TRUE)
result_path <- if (length(args) >= 1) args[[1]] else "simulation/results/repair-seed-1-64.tsv"
cycle_path <- if (length(args) >= 2) args[[2]] else "simulation/results/repair-seed-1-64-cycles.tsv"
summary_path <- if (length(args) >= 3) args[[3]] else "simulation/results/repair-seed-1-64-summary.md"
figure_path <- if (length(args) >= 4) args[[4]] else "figures/developmental-repair-bootstrap.png"

raw <- read.delim(result_path, sep = "\t", quote = "", stringsAsFactors = FALSE)
cycles <- read.delim(cycle_path, sep = "\t", quote = "", stringsAsFactors = FALSE)
number <- function(key, x) as.numeric(sub(paste0(".*", key, "=([0-9.]+).*"), "\\1", x))
logical_value <- function(key, x) sub(paste0(".*", key, "=([^ ]+).*"), "\\1", x) == "true"

raw$initial_bridged <- number("bridge_metal", raw$result) > 0 & number("frontier", raw$result) >= 190
raw$cycles_completed <- number("repair_cycles_completed", raw$result)
raw$failures <- number("repair_failures", raw$result)
raw$repaired <- logical_value("repaired", raw$result)
last_cycle <- max(cycles$cycle)
raw$completed_horizon <- raw$cycles_completed == last_cycle & raw$failures == 0 & raw$repaired

wide <- reshape(cycles[, c("seed", "cycle", "steps")], idvar = "seed", timevar = "cycle", direction = "wide")
last_steps <- paste0("steps.", last_cycle)
paired <- wide[complete.cases(wide[, c("steps.1", last_steps)]), ]
paired$gain <- paired$steps.1 - paired[[last_steps]]

set.seed(319)
boot <- replicate(10000, mean(sample(paired$gain, nrow(paired), replace = TRUE)))
ci <- unname(quantile(boot, c(0.025, 0.975)))
fmt <- function(x, digits = 2) formatC(x, digits = digits, format = "f")

cycle_summary <- aggregate(cbind(steps, added, removed) ~ cycle, data = cycles, FUN = median)
immediate <- aggregate(I(steps == 0) ~ cycle, data = cycles, FUN = mean)
names(immediate)[2] <- "immediate_fraction"
cycle_summary <- merge(cycle_summary, immediate, by = "cycle")

lines <- c(
  "# Developmental repair bootstrap",
  "",
  sprintf("- Independent seeds: **%d**.", nrow(raw)),
  sprintf("- Initial bridges formed: **%d/%d**.", sum(raw$initial_bridged), nrow(raw)),
  sprintf("- Completed the full %d-epoch observation horizon without a failed epoch: **%d/%d**.", last_cycle, sum(raw$completed_horizon), nrow(raw)),
  sprintf("- Paired first-to-final observed repair-step gain: **%s steps**; 95%% bootstrap CI **[%s, %s]** across %d complete pairs.", fmt(mean(paired$gain)), fmt(ci[1]), fmt(ci[2]), nrow(paired)),
  "",
  "| Cycle | Median repair steps | Median cells added | Immediate survival |",
  "|---:|---:|---:|---:|",
  sprintf("| %d | %s | %s | %s%% |", cycle_summary$cycle, fmt(cycle_summary$steps, 1), fmt(cycle_summary$added, 1), fmt(100 * cycle_summary$immediate_fraction, 1)),
  "",
  "Repeated damage supports path-dependent repair adaptation when the paired confidence interval for first-to-final observed repair steps lies entirely above zero. An interval containing zero retains the no-developmental-improvement null."
)
writeLines(lines, summary_path)

png(figure_path, width = 1500, height = 900, res = 160, type = "quartz", bg = "#05070B")
par(mar = c(5, 5, 3, 1), bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF")
boxplot(steps ~ cycle, data = cycles, col = "#B48CFF", border = "#E5D8FF",
        xlab = "damage epoch", ylab = "repair steps", main = "Repair time across repeated damage", col.main = "#FFFFFF")
abline(h = 0, col = "#70D7FF", lwd = 2)
dev.off()

cat(paste(lines, collapse = "\n"), "\n")
