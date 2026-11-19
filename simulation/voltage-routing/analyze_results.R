names <- c("straight-wire", "parallel-grid", "grown-cherenkov", "grown-cherenkov-development")
labels <- c("Straight wire", "Parallel grid", "Grown Cherenkov", "Recurrently developed")

read_final <- function(path) tail(read.csv(path), 1)

uncut <- do.call(rbind, lapply(names, function(name) read_final(paste0(name, ".csv"))))
cut <- do.call(rbind, lapply(names, function(name) read_final(paste0(name, "-cut.csv"))))

electrode_fraction <- 6 / 192
result <- data.frame(
  topology = labels,
  metal_fraction = uncut$metal_fraction,
  interconnect_fraction = uncut$metal_fraction - electrode_fraction,
  flux = uncut$terminal_flux,
  flux_per_interconnect = uncut$terminal_flux / (uncut$metal_fraction - electrode_fraction),
  cut_flux = cut$terminal_flux,
  retained_percent = 100 * cut$terminal_flux / uncut$terminal_flux
)

write.table(result, "results.tsv", sep = "\t", row.names = FALSE, quote = FALSE)

fmt <- function(x, digits = 6) formatC(x, digits = digits, format = "f")
markdown <- c(
  "# First MOOSE voltage-routing result",
  "",
  "MOOSE solved `div(sigma * grad(V)) = 0` on three initial image-derived topologies and one developed follow-up with identical one-volt source and sink boundaries. Metal conductivity was normalized to `1`; surrounding-medium conductivity was `1e-6`. Each topology included identical three-pixel terminal bus bars. The cut removed one seven-by-seven-pixel region nearest the interconnect center.",
  "",
  "| Topology | Interconnect fraction | Terminal flux | Flux / interconnect | Flux after cut | Retained |",
  "|---|---:|---:|---:|---:|---:|",
  sprintf("| %s | %s | %s | %s | %s | %s%% |", result$topology, fmt(result$interconnect_fraction), fmt(result$flux), fmt(result$flux_per_interconnect), format(result$cut_flux, scientific = TRUE, digits = 5), fmt(result$retained_percent, 3)),
  "",
  "The straight wire delivered the greatest conductance per unit interconnect and lost its path under one cut. The five-rail grid delivered the greatest absolute terminal flux and retained 80% after the cut. The first grown Cherenkov topology delivered the least conductance per unit interconnect and lost its path under the cut.",
  "",
  "After recurrent cut-and-regrow epochs, the developed topology retained essentially all of its MOOSE terminal flux under the practiced local cut while using less interconnect area than the grid. Its absolute flux and conductance per unit material remained far below the grid. Repeated injury earned location-specific redundancy; the next developmental pressure must reward delivered current and useful capacity across multiple terminal configurations."
)
writeLines(markdown, "RESULTS.md")

png("../../figures/voltage-routing-benchmark.png", width = 1600, height = 960, res = 160, type = "quartz", bg = "#05070B")
par(mfrow = c(1, 2), mar = c(7, 5, 3, 1), oma = c(0, 0, 2, 0), bg = "#05070B", fg = "#EAF8FF", col.axis = "#C9D9E2", col.lab = "#EAF8FF")
barplot(result$flux_per_interconnect, names.arg = result$topology, las = 2,
        col = c("#F2F5F7", "#9DE7C1", "#48BDF0", "#B48CFF"), border = NA,
        ylab = "terminal flux / interconnect fraction", main = "Material efficiency", col.main = "#FFFFFF")
barplot(result$retained_percent, names.arg = result$topology, las = 2,
        col = c("#F2F5F7", "#9DE7C1", "#48BDF0", "#B48CFF"), border = NA,
        ylab = "flux retained after cut (%)", main = "Single-cut recovery", col.main = "#FFFFFF")
mtext("MOOSE voltage-routing benchmark", outer = TRUE, side = 3, line = 0.2, col = "#FFFFFF", cex = 1.4, font = 2)
dev.off()
