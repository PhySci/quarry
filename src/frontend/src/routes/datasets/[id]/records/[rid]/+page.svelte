<script lang="ts">
  import { onMount } from 'svelte';
  import SpanHighlight from '$lib/components/SpanHighlight.svelte';
  import { api, type Entity, type RecordItem } from '$lib/api';
  import type { PageData } from './$types';

  export let data: PageData;

  let record: RecordItem | null = null;
  let text = '';
  let entitiesJson = '[]';
  let error = '';
  let saved = false;

  $: datasetId = data.params.id;
  $: recordId = data.params.rid;

  onMount(loadRecord);

  async function loadRecord() {
    record = await api.getRecord(datasetId, recordId);
    text = record.text;
    entitiesJson = JSON.stringify(record.entities, null, 2);
  }

  async function saveRecord() {
    error = '';
    saved = false;
    try {
      const entities = JSON.parse(entitiesJson) as Entity[];
      record = await api.updateRecord(datasetId, recordId, { text, entities });
      text = record.text;
      entitiesJson = JSON.stringify(record.entities, null, 2);
      saved = true;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Не удалось сохранить запись';
    }
  }
</script>

<section class="grid">
  <p><a href={`/datasets/${datasetId}`}>← К записям</a></p>

  {#if record}
    <div class="card">
      <h1>Запись</h1>
      <SpanHighlight text={record.text} entities={record.entities} />
      <p class="muted">Создана: {new Date(record.created_at).toLocaleString()}</p>
      <p class="muted">Обновлена: {new Date(record.updated_at).toLocaleString()}</p>
    </div>

    <form class="card grid" on:submit|preventDefault={saveRecord}>
      <h2>Редактирование</h2>
      <label>
        Текст
        <textarea bind:value={text}></textarea>
      </label>
      <label>
        Entities JSON
        <textarea bind:value={entitiesJson}></textarea>
      </label>
      <div class="row">
        <button type="submit">Сохранить</button>
        {#if saved}<span class="muted">Сохранено</span>{/if}
      </div>
      {#if error}
        <p class="error">{error}</p>
      {/if}
    </form>
  {:else}
    <p class="muted">Загрузка...</p>
  {/if}
</section>
