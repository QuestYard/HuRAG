  # agentic 检索算法：
  # 1. 提取 low level keywords 和 high level keywords，分别用 ", " 连接为字符串;
  # 2. 使用 low level keywords 字符串搜索最相似的 entity_top_k 个 entities
  #    及其直接关联的 relations，得到 local entities (相似度排序) 和
  #    local relations (先 degree，后 relation weight 排序);
  # 3. 使用 high level keywords 字符串搜索最相似的 relation_top_k 个 relations
  #    及其两个端点上的 entities，得到 global entities (按 relations 序先 src 后 tgt)
  #    和 global relations (相似度排序);
  # 4. 使用 query 搜索最相似的 segment_top_k 个 query_segments (相似度序);
  # 5. 使用 Round-robin 归并 local entities 和 global entities，得到 final entities：
  #    - 按照先 local 后 global 的次序，从向量相似度由高到低逐个抽取；
  #    - 如有重复直接跳过。
  # 6. 使用 Round-robin 归并 local 和 global relations 为 final relations;
  # 7. 归并根据 query 搜索得到的 segments 和 final entities, final relations 上引用
  #    的 segments：
  #    - 在 final entities 所引用的所有 segments 中搜索最多 2 倍于实体数的与 query
  #      最相似的 entity_segments;
  #    - 在 final relations 所引用的所有 segments 中做同样的搜索，在搜索前先依照上
  #      一步得到的 entity_segments 进行去重，得到 relation_segments;
  #    - 使用 Round-robin 归并 query_segments, entity_segments, relation_segments
  #    - rerank 最终的 segments，返回前 segment_top_k 个。

