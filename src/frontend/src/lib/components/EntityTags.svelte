<script lang="ts">
  import type { Entity } from '$lib/api';

  export let entities: Entity[] = [];
</script>

{#if entities.length}
  {#each entities as entity}
    <span class="tag">{entity.label}: {entity.start}-{entity.end}</span>
  {/each}
{:else}
  <span class="muted">Нет сущностей</span>
{/if}
