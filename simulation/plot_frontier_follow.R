args <- commandArgs(trailingOnly = TRUE)
input <- if (length(args) >= 1) args[[1]] else "simulation/output/frontier-follow.csv"
output <- if (length(args) >= 2) args[[2]] else "figures/frontier-follow-trajectory.png"

d <- read.csv(input)

png(
  output,
  width = 1600, height = 1040, res = 160,
  type = "quartz", bg = "#05070B", pointsize = 13
)
par(
  mfrow = c(2, 1),
  mar = c(3.2, 4.5, 2.2, 1.2),
  oma = c(1.2, 0, 2.2, 0),
  bg = "#05070B",
  fg = "#EAF8FF",
  col.axis = "#C9D9E2",
  col.lab = "#EAF8FF"
)

plot(
  d$step, d$frontier_x,
  type = "l", lwd = 3, col = "#F7FAFF",
  xlab = "", ylab = "frontier x",
  main = "Conductive frontier",
  col.main = "#EAF8FF"
)
grid(col = "#24333E")
points(tail(d$step, 1), tail(d$frontier_x, 1), pch = 19, col = "#70D7FF")

plot(
  d$step, d$light_center,
  type = "l", lwd = 3, col = "#48BDF0",
  ylim = c(0, 1),
  xlab = "simulation step", ylab = "photon-band center",
  main = "Light repositioned from the leading edge",
  col.main = "#EAF8FF"
)
grid(col = "#24333E")
points(tail(d$step, 1), tail(d$light_center, 1), pch = 19, col = "#FFFFFF")

mtext(
  "Frontier-following photon loop · seed 319",
  outer = TRUE, side = 3, line = 0.5,
  col = "#FFFFFF", cex = 1.35, font = 2
)
dev.off()
