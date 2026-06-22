<script lang="ts">
  import { onMount } from 'svelte';
  import EntityTags from '$lib/components/EntityTags.svelte';
  import { api, type Dataset, type ImportJob, type RecordItem } from '$lib/api';
  import type { PageData } from './$types';

  export let data: PageData;

  let dataset: Dataset | null = null;
  let records: RecordItem[] = [];
  let total = 0;
  let q = '';
  let text = '';
  let file: File | null = null;
  let importJob: ImportJob | null = null;
  let error = '';

  $: datasetId = data.params.id;

  onMount(async () => {
    await Promise.all([loadDataset(), loadRecords()]);
  });

  async function loadDataset() {
    dataset = await api.getDataset(datasetId);
  }

  async function loadRecords() {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    const response = await api.listRecords(datasetId, params.toString() ? `?${params}` : '');
    records = response.items;
    total = response.total;
  }

  async function createRecord() {
    if (!text.trim()) return;
    const record = await api.createRecord(datasetId, { text });
    records = [record, ...records];
    text = '';
    total += 1;
  }

  async function uploadJsonl() {
    if (!file) return;
    error = '';
    importJob = await api.importJsonl(datasetId, file);
    pollImport(importJob.id);
  }

  async function pollImport(jobId: string) {
    const job = await api.getImportJob(datasetId, jobId);
    importJob = job;
    if (job.status === 'pending' || job.status === 'running') {
      setTimeout(() => pollImport(jobId), 2000);
    } else {
      await loadRecords();
      await loadDataset();
    }
  }
</script>

<section class="grid">
  <p><a href="/">← К датасетам</a></p>

  <div class="card">
    <h1>{dataset?.name ?? 'Датасет'}</h1>
    {#if dataset?.description}
      <p class="muted">{dataset.description}</p>
    {/if}
    <p class="muted">Записей: {dataset?.records_count ?? total}</p>
  </div>

  <form class="card grid" on:submit|preventDefault={createRecord}>
    <h2>Добавить запись</h2>
    <textarea bind:value={text} placeholder="Текст записи"></textarea>
    <button type="submit">Добавить</button>
  </form>

  <div class="card grid">
    <h2>Импорт JSONL</h2>
    <input type="file" accept=".jsonl" on:change={(event) => (file = event.currentTarget.files?.[0] ?? null)} />
    <button type="button" on:click={uploadJsonl}>Импортировать</button>
    {#if importJob}
      <p class="muted">
        Статус: {importJob.status}, загружено: {importJob.loaded_count}, пропущено: {importJob.skipped_count},
        ошибок: {importJob.error_count}
      </p>
    {/if}
  </div>

  <div class="card grid">
    <div class="row wrap">
      <input bind:value={q} placeholder="Поиск по тексту" />
      <button type="button" on:click={loadRecords}>Искать</button>
    </div>

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <h2>Записи ({total})</h2>
    {#if records.length === 0}
      <p class="muted">Записей пока нет.</p>
    {:else}
      <table>
        <thead>
          <tr>
            <th>Текст</th>
            <th>Сущности</th>
            <th>Создана</th>
          </tr>
        </thead>
        <tbody>
          {#each records as record}
            <tr>
              <td><a href={`/datasets/${datasetId}/records/${record.id}`}>{record.text.slice(0, 140)}</a></td>
              <td><EntityTags entities={record.entities} /></td>
              <td>{new Date(record.created_at).toLocaleString()}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</section>
