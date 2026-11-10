# Broken Sample

Good relative link: [guide](docs/guide.md)
Missing file: [missing](docs/missing.md)
Missing same-file anchor: [nope](#no-such-heading)
Existing same-file anchor: [here](#broken-sample)
Cross-file good: [getting started](docs/guide.md#getting-started)
Cross-file bad: [bad](docs/guide.md#missing-section)
External: [example](https://example.com/page)

```markdown
[fenced missing](docs/not-real.md)
[fenced external](https://example.com/fenced)
```

Inline `[inline missing](docs/not-real.md)` stays quiet.

Image is ignored: ![shot](assets/missing.png)
