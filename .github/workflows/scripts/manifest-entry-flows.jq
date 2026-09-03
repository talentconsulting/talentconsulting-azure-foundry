def flowdefs: {
  "openapi": {"nodeKeys": ["specs"], "agent": "openapi-spec-workflow"},
  "dbschema": {"nodeKeys": ["dbschema", "db-schema"], "agent": "dbschema-workflow"},
  "eventcatalog": {"nodeKeys": ["eventcatalog", "event-catalog"], "agent": "eventcatalog-workflow"},
  "service-dependency": {"nodeKeys": ["service-dependencies"], "agent": "service-dependency-workflow"},
  "c4": {"nodeKeys": ["c4"], "agent": "c4-workflow"},
  "local-dev-config": {"nodeKeys": ["local-dev-config"], "agent": "local-dev-config-workflow"}
};

# Inputs: $repo (github-repo to match) and $keys (requested flow keys, or null for all).
# Reads the manifest array from stdin/file and resolves it to a matrix of
# {key, agent, source_url} entries for the matched repository,
# using each flow's own "path-to-scan" from the manifest -- not one shared source URL.
(($repo | rtrimstr("/"))) as $wantRepo
| (map(select((.["github-repo"] // "" | rtrimstr("/")) == $wantRepo)) | first) as $entry
| if $entry == null then
    {error: ("No manifest entry found for github-repo " + $repo)}
  else
    (flowdefs
     | to_entries
     | map(
         . as $f
         | ($entry | to_entries | map(select(.key as $k | $f.value.nodeKeys | index($k))) | first) as $match
         | select($match != null)
         | select($keys == null or ($keys | index($f.key)) != null)
         | {
             key: $f.key,
             agent: $f.value.agent,
             source_url: (($entry["github-repo"] | rtrimstr("/")) + "/" + $match.value["path-to-scan"])
           }
       )) as $matrix
    | if ($matrix | length) == 0 then
        {error: "Manifest entry matched but no requested flow nodes were present"}
      else
        {matrix: $matrix}
      end
  end
