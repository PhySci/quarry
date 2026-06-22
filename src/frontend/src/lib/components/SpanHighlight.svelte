<script lang="ts">
  import type { Entity } from '$lib/api';

  export let text = '';
  export let entities: Entity[] = [];

  $: segments = buildSegments(text, entities);

  function buildSegments(source: string, spans: Entity[]) {
    const sorted = [...spans].sort((a, b) => a.start - b.start);
    const result: Array<{ text: string; label?: string }> = [];
    let cursor = 0;

    for (const span of sorted) {
      if (span.start > cursor) {
        result.push({ text: source.slice(cursor, span.start) });
      }
      result.push({ text: source.slice(span.start, span.end), label: span.label });
      cursor = span.end;
    }

    if (cursor < source.length) {
      result.push({ text: source.slice(cursor) });
    }

    return result;
  }
</script>

<p class="highlighted-text">
  {#each segments as segment}
    {#if segment.label}
      <mark>{segment.text}<small>{segment.label}</small></mark>
    {:else}
      <span>{segment.text}</span>
    {/if}
  {/each}
</p>

<style>
  .highlighted-text {
    line-height: 2;
    white-space: pre-wrap;
  }

  mark {
    background: #fff2b8;
    border-radius: 6px;
    padding: 2px 4px;
  }

  small {
    color: #6b5b00;
    font-size: 10px;
    font-weight: 700;
    margin-left: 4px;
  }
</style>
