d <- read.delim("ablation/moose-flux.tsv")
d$lesion <- as.integer(d$lesion)

lines <- c(
  "# Progressive targeted ablation",
  "",
  "At each epoch, the shortest surviving source-to-sink path was identified and a seven-by-seven-pixel lesion was centered on that path. MOOSE then recomputed terminal flux.",
  "",
  "| Topology | First disconnecting lesion | Initial flux | Flux after first lesion |",
  "|---|---:|---:|---:|",
  sprintf("| %s | %d | %.6f | %.6g |",
          c("Straight wire", "Parallel grid", "Recurrently developed topology"),
          c(1, 5, 1),
          vapply(c("straight", "grid", "developed"), function(x) d$terminal_flux[d$topology == x & d$lesion == 0], numeric(1)),
          vapply(c("straight", "grid", "developed"), function(x) d$terminal_flux[d$topology == x & d$lesion == 1], numeric(1))),
  "",
  "The developed topology retained 99.975% of flux under the recurrent local lesion, yet disconnected under the first lesion aimed at its current shortest path. Its adaptation was location-specific. The parallel grid generalized across four targeted rail failures and disconnected on the fifth."
)
writeLines(lines, "ablation/RESULTS.md")

png("../../figures/progressive-targeted-ablation.png", width = 1500, height = 900, res = 160, type = "quartz", bg = "#05070B")
par(mar = c(5, 5, 3, 1), bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF")
colors <- c(straight = "#F2F5F7", grid = "#9DE7C1", developed = "#B48CFF")
plot(NA, xlim = range(d$lesion), ylim = range(d$terminal_flux[d$terminal_flux > 0]), log = "y",
     xlab = "targeted lesion number", ylab = "MOOSE terminal flux", main = "Progressive shortest-path ablation", col.main = "#FFFFFF")
for (name in names(colors)) {
  x <- d[d$topology == name, ]
  lines(x$lesion, x$terminal_flux, type = "o", lwd = 3, pch = 19, col = colors[[name]])
}
legend("topright", legend = c("straight wire", "parallel grid", "recurrently developed"),
       col = colors, lwd = 3, pch = 19, bty = "n", text.col = "white")
dev.off()

cat(paste(lines, collapse = "\n"), "\n")
