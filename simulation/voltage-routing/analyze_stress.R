files <- c(
  "Straight wire" = "stress-straight.csv",
  "Parallel grid" = "stress-parallel-grid.csv",
  "Grown Cherenkov" = "stress-grown-cherenkov.csv",
  "Recurrently developed" = "stress-grown-cherenkov-development.csv"
)

result <- do.call(rbind, lapply(names(files), function(name) {
  x <- tail(read.csv(files[[name]]), 1)
  data.frame(topology = name, x[, setdiff(names(x), "time")], row.names = NULL)
}))

reference_current <- result$terminal_flux[result$topology == "Straight wire"]
result$equal_current_voltage <- reference_current / result$terminal_flux
result$equal_current_joule <- result$joule_integral * result$equal_current_voltage^2
result$equal_current_peak_current <- result$peak_current_density * result$equal_current_voltage
write.table(result, "field-stress.tsv", sep = "\t", row.names = FALSE, quote = FALSE)

fmt <- function(x, digits = 6) formatC(x, digits = digits, format = "f")
lines <- c(
  "# Field and dissipation result",
  "",
  "MOOSE computed voltage gradients, current-density proxy, and Joule density on the same finite-element state used for terminal flux. The Joule integral agrees with boundary power at one normalized volt.",
  "",
  "| Topology | Joule at ΔV=1 | Peak current density | Voltage for straight-wire current | Joule at straight-wire current |",
  "|---|---:|---:|---:|---:|",
  sprintf("| %s | %s | %s | %s | %s |", result$topology, fmt(result$joule_integral), fmt(result$peak_current_density), fmt(result$equal_current_voltage, 3), fmt(result$equal_current_joule)),
  "",
  "At equal voltage, both grown topologies dissipate less total power because they carry less current. Their local peak current-density proxies remain slightly above the wire and grid. At equal delivered current, the grown topologies require higher voltage and dissipate more power. Low total flux therefore identifies a low-power state, not uniformly low local electrical stress."
)
writeLines(lines, "FIELD_STRESS.md")

png("../../figures/field-stress-boundaries.png", width = 1600, height = 960, res = 160, type = "quartz", bg = "#05070B")
par(mfrow = c(1, 2), mar = c(8, 5, 3, 1), oma = c(0, 0, 2, 0), bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF")
colors <- c("#F2F5F7", "#9DE7C1", "#48BDF0", "#B48CFF")
barplot(result$joule_integral, names.arg = result$topology, las = 2, col = colors, border = NA,
        ylab = "integrated Joule density", main = "Equal voltage: ΔV = 1", col.main = "#FFFFFF")
barplot(result$equal_current_joule, names.arg = result$topology, las = 2, col = colors, border = NA,
        ylab = "integrated Joule density", main = "Equal straight-wire current", col.main = "#FFFFFF")
mtext("Boundary conditions reverse the stress interpretation", outer = TRUE, side = 3, line = 0.2, col = "#FFFFFF", cex = 1.35, font = 2)
dev.off()

cat(paste(lines, collapse = "\n"), "\n")
