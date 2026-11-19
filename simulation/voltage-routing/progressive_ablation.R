source("generate_fixed_topologies.R")

find_path <- function(m) {
  active <- m == "white"
  n <- w * h
  parent <- rep(-1L, n)
  queue <- integer(n)
  head <- 1L
  tail <- 0L
  to_id <- function(row, col) (row - 1L) * w + col
  to_row <- function(id) ((id - 1L) %/% w) + 1L
  to_col <- function(id) ((id - 1L) %% w) + 1L

  for (row in which(active[, 1])) {
    id <- to_id(row, 1L)
    parent[id] <- 0L
    tail <- tail + 1L
    queue[tail] <- id
  }

  goal <- NA_integer_
  while (head <= tail && is.na(goal)) {
    current <- queue[head]
    head <- head + 1L
    row <- to_row(current)
    col <- to_col(current)
    if (col == w) {
      goal <- current
      break
    }
    for (dr in -1:1) {
      for (dc in -1:1) {
        if (dr == 0 && dc == 0) next
        rr <- row + dr
        cc <- col + dc
        if (rr < 1 || rr > h || cc < 1 || cc > w || !active[rr, cc]) next
        neighbor <- to_id(rr, cc)
        if (parent[neighbor] == -1L) {
          parent[neighbor] <- current
          tail <- tail + 1L
          queue[tail] <- neighbor
        }
      }
    }
  }

  if (is.na(goal)) return(NULL)
  path <- integer()
  current <- goal
  while (current != 0L) {
    path <- c(current, path)
    current <- parent[current]
  }
  cbind(row = to_row(path), col = to_col(path))
}

ablate <- function(m, radius = 3, maximum = 100) {
  states <- list(m)
  rows <- data.frame(lesion = 0L, connected = TRUE, metal_fraction = mean(m == "white"))
  for (lesion in seq_len(maximum)) {
    path <- find_path(m)
    if (is.null(path)) break
    eligible <- path[path[, "col"] > 3 & path[, "col"] < w - 2, , drop = FALSE]
    score <- abs(eligible[, "col"] - w / 2) * 10 + abs(eligible[, "row"] - h / 2)
    target <- eligible[which.min(score), ]
    rr <- max(1, target[["row"]] - radius):min(h, target[["row"]] + radius)
    cc <- max(4, target[["col"]] - radius):min(w - 3, target[["col"]] + radius)
    m[rr, cc] <- "black"
    connected <- !is.null(find_path(m))
    states[[length(states) + 1L]] <- m
    rows <- rbind(rows, data.frame(lesion = lesion, connected = connected, metal_fraction = mean(m == "white")))
    if (!connected) break
  }
  list(states = states, rows = rows)
}

topologies <- list(
  straight = straight,
  grid = grid,
  developed = development
)

dir.create("ablation", showWarnings = FALSE)
all_results <- data.frame()
for (name in names(topologies)) {
  result <- ablate(topologies[[name]])
  for (i in seq_along(result$states)) {
    write_topology(result$states[[i]], sprintf("ablation/%s-%03d.png", name, i - 1L))
  }
  result$rows$topology <- name
  all_results <- rbind(all_results, result$rows[, c("topology", "lesion", "connected", "metal_fraction")])
}
write.table(all_results, "ablation/connectivity.tsv", sep = "\t", row.names = FALSE, quote = FALSE)
print(all_results[!duplicated(all_results$topology, fromLast = TRUE), ])
