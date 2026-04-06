## Brief overview
This rule ensures that news scanning and AI filtering operations remain efficient and cost-effective by limiting the number of articles processed.

## Performance and Cost Optimization
- **Scan Limits**: Always keep the number of articles sent to the AI for filtering to less than 30.
- **Token Efficiency**: When processing a pool of articles, prefer sending only metadata (like Titles and IDs) to the LLM to minimize token usage. Full article details (links, images) should be re-attached after the AI has made its selection.
- **Diversity**: Shuffle raw scraped data before limiting the pool to ensure the AI considers a representative sample from all sources and categories.