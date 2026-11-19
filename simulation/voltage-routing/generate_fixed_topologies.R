w <- 192
h <- 128

write_topology <- function(m, path) {
  png(path, width = w, height = h, type = "quartz", bg = "black")
  par(mar = c(0, 0, 0, 0), xaxs = "i", yaxs = "i")
  plot(c(0, 1), c(0, 1), type = "n", axes = FALSE, xlab = "", ylab = "")
  rasterImage(as.raster(m), 0, 0, 1, 1, interpolate = FALSE)
  dev.off()
}

cut_near_center <- function(m, radius = 3) {
  metal <- which(m == "white", arr.ind = TRUE)
  score <- abs(metal[, "col"] - w / 2) * 10 + abs(metal[, "row"] - h / 2)
  target <- metal[which.min(score), ]
  rows <- max(1, target[["row"]] - radius):min(h, target[["row"]] + radius)
  cols <- max(4, target[["col"]] - radius):min(w - 3, target[["col"]] + radius)
  m[rows, cols] <- "black"
  m
}

read_pgm_topology <- function(path) {
  connection <- file(path, "rb")
  on.exit(close(connection))
  magic <- readLines(connection, n = 1)
  dimensions <- as.integer(strsplit(readLines(connection, n = 1), " +")[[1]])
  maximum <- as.integer(readLines(connection, n = 1))
  stopifnot(magic == "P5", all(dimensions == c(w, h)), maximum == 255)
  pixels <- readBin(connection, what = "integer", n = w * h, size = 1, signed = FALSE)
  topology <- matrix(ifelse(pixels > 127, "white", "black"), nrow = h, byrow = TRUE)
  topology[, 1:3] <- "white"
  topology[, (w - 2):w] <- "white"
  topology
}

straight <- matrix("black", nrow = h, ncol = w)
straight[(h / 2 - 1):(h / 2 + 1), ] <- "white"
straight[, 1:3] <- "white"
straight[, (w - 2):w] <- "white"

grid <- matrix("black", nrow = h, ncol = w)
for (y in round(seq(16, h - 15, length.out = 5))) {
  grid[pmax(1, y - 1):pmin(h, y + 1), ] <- "white"
}
grid[, 1:3] <- "white"
grid[, (w - 2):w] <- "white"

dir.create("topologies", showWarnings = FALSE)
write_topology(straight, "topologies/straight-wire.png")
write_topology(grid, "topologies/parallel-grid.png")
write_topology(cut_near_center(straight), "topologies/straight-wire-cut.png")
write_topology(cut_near_center(grid), "topologies/parallel-grid-cut.png")

grown_path <- "../output/cherenkov.metal.pgm"
if (file.exists(grown_path)) {
  grown <- read_pgm_topology(grown_path)
  write_topology(grown, "topologies/grown-cherenkov.png")
  write_topology(cut_near_center(grown), "topologies/grown-cherenkov-cut.png")
}

repaired_path <- "../output/cherenkov-repair-long.metal.pgm"
if (file.exists(repaired_path)) {
  repaired <- read_pgm_topology(repaired_path)
  write_topology(repaired, "topologies/grown-cherenkov-repaired.png")
}

development_path <- "../output/cherenkov-development.metal.pgm"
if (file.exists(development_path)) {
  development <- read_pgm_topology(development_path)
  write_topology(development, "topologies/grown-cherenkov-development.png")
  write_topology(cut_near_center(development), "topologies/grown-cherenkov-development-cut.png")
}

transect_60_path <- "../output/transect-60.metal.pgm"
if (file.exists(transect_60_path)) {
  transect_60 <- read_pgm_topology(transect_60_path)
  write_topology(transect_60, "topologies/grown-transect-60.png")
  write_topology(cut_near_center(transect_60), "topologies/grown-transect-60-cut.png")
}
