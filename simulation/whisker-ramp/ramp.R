rho <- 11.5e-8
length_m <- 0.875e-3
initial_diameter_um <- 1
measured_diameter <- c(1, 2.5, 4)
measured_fusing_current <- c(0.010, 0.030, 0.075)
fit <- lm(log(measured_fusing_current) ~ log(measured_diameter))
a <- exp(coef(fit)[1])
b <- unname(coef(fit)[2])

resistance <- function(diameter_um) {
  area <- pi * (diameter_um * 1e-6 / 2)^2
  rho * length_m / area
}

fusing_current <- function(diameter_um) a * diameter_um^b

required_diameter <- function(voltage, series_resistance) {
  margin <- function(diameter_um) {
    0.8 * fusing_current(diameter_um) -
      voltage / (series_resistance + resistance(diameter_um))
  }
  if (margin(initial_diameter_um) >= 0) return(initial_diameter_um)
  if (margin(1000) < 0) return(NA_real_)
  uniroot(margin, c(initial_diameter_um, 1000))$root
}

series_values <- c(10000, 1000, 100, 1)
voltages <- seq(0, 100, by = 0.25)
result <- do.call(rbind, lapply(series_values, function(series_resistance) {
  data.frame(
    voltage = voltages,
    series_resistance = series_resistance,
    fixed_current = voltages / (series_resistance + resistance(initial_diameter_um)),
    fixed_fused = voltages / (series_resistance + resistance(initial_diameter_um)) > fusing_current(initial_diameter_um),
    maintained_diameter_um = vapply(voltages, required_diameter, numeric(1), series_resistance = series_resistance),
    source_current_capability = voltages / series_resistance
  )
}))
result$vacuum_arc_capable <- result$voltage >= 18 & result$source_current_capability >= 3
write.table(result, "ramp.tsv", sep = "\t", row.names = FALSE, quote = FALSE)

selected <- result[result$voltage %in% c(10, 48, 100), ]
write.table(selected, "selected-points.tsv", sep = "\t", row.names = FALSE, quote = FALSE)

png("../../figures/tin-whisker-voltage-ramp.png", width = 1600, height = 950, res = 160, type = "quartz", bg = "#05070B")
par(mar = c(5, 5, 3, 1), bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF")
colors <- c("10000" = "#F2F5F7", "1000" = "#9DE7C1", "100" = "#48BDF0", "1" = "#B48CFF")
plot(NA, xlim = range(voltages), ylim = c(1, 1000), log = "y",
     xlab = "supply voltage", ylab = "maintained solid-path diameter (µm)",
     main = "Tin path required below the measured fusing envelope", col.main = "#FFFFFF")
for (series_resistance in series_values) {
  x <- result[result$series_resistance == series_resistance, ]
  lines(x$voltage, x$maintained_diameter_um, lwd = 3, col = colors[[as.character(series_resistance)]])
}
abline(v = c(10, 48), col = c("#FFD36A", "#FF7B7B"), lty = 2, lwd = 2)
abline(h = 4, col = "#9AA7B2", lty = 3)
legend("bottomright", legend = paste0(series_values, " Ω series"), col = colors, lwd = 3, bty = "n", text.col = "white")
text(10, 180, "10 V documented stable short", srt = 90, col = "#FFD36A", pos = 4)
text(48, 180, "48 V documented self-erasure", srt = 90, col = "#FF7B7B", pos = 4)
dev.off()

cat(sprintf("fit: I_fuse = %.6g * diameter_um^%.6f\n", a, b))
print(selected)
