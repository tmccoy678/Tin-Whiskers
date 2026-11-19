# Anonymous two-page extended abstract

Final deliverables:

- `Adaptive_Conductive_Topology_Extended_Abstract_Anonymous.docx`
- `Adaptive_Conductive_Topology_Extended_Abstract_Anonymous.pdf`

The PDF is exactly two US-letter pages. The DOCX uses 12-point Times New Roman
throughout, carries anonymous core metadata, and passed ZIP integrity checks.
The PDF reports `Anonymous` as author and passed the two-page metadata and
rendered-page review.

## Figures

- `figures/figure1-branching-comparators.png`
  (`7d1e9eea026dcb10d151b6d98ea8db259ca6039aa8056107ac1c253792e657b0`)
- `figures/figure2-remodel-and-repair.png`
  (`b3fea970e2cc897eb4dd6ad1d5c9454552c27a8a80e4bee32b8c3da81f1e88f3`)

Figure 1 labels human H01, public-domain pigeon Purkinje, adaptive lattice,
and simulated 3D physics as distinct evidence classes. Figure 2 labels fixed
remodeling and the literal cut sequence, including first reconnection at epoch
18. `FIGURE_PLAN.md` records source paths, hashes, attribution, and acceptance
checks.

## Rebuild

```zsh
./render_figures.py
pandoc EXTENDED_ABSTRACT_DRAFT.md \
  --from=gfm+yaml_metadata_block \
  --reference-doc=/absolute/path/to/AgentVerify_Extended_Abstract_Template.docx \
  --resource-path=. \
  --output=Adaptive_Conductive_Topology_Extended_Abstract_Anonymous.docx
./format_docx_12pt.zsh input.docx output.docx
```

Microsoft Word produced the final PDF from the formatted DOCX. The rebuild path
uses Pandoc and Word rather than `python-docx`.
