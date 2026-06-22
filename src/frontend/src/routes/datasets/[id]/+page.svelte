<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import EntityTags from '$lib/components/EntityTags.svelte';
  import {
    api,
    type Dataset,
    type DatasetStats,
    type ExportFormat,
    type ImportJob,
    type RecordItem,
    type RecordSort
  } from '$lib/api';
  import type { PageData } from './$types';

  export let data: PageData;

  let dataset: Dataset | null = null;
  let stats: DatasetStats | null = null;
  let records: RecordItem[] = [];
  let total = 0;
  let text = '';
  let file: File | null = null;
  let duplicateMode = 'skip';
  let importJob: ImportJob | null = null;
  let error = '';
  let loading = false;

  let q = '';
  let selectedLabels: string[] = [];
  let hasEntities = '';
  let sort: RecordSort = 'created_at_desc';
  let pageNumber = 1;
  const pageSize = 50;

  const exportFormats: { value: ExportFormat; label: string }[] = [
    { value: 'jsonl', label: 'JSONL' },
    { value: 'conll', label: 'CoNLL-2003' },
    { value: 'spacy', label: 'SpaCy v3' },
    { value: 'csv', label: 'CSV' }
  ];

  $: datasetId = data.params.id;
  $: availableLabels = stats ? Object.keys(stats.labels).sort() : [];
  $: totalPages = Math.max(1, Math.ceil(total / pageSize));
  $: currentFilters = {
    q: q || undefined,
    labels: selectedLabels.join(',') || undefined,
    has_entities: hasEntities || undefined,
    sort
  };

  onMount(() => {
    syncFromUrl();
    void loadDataset();
    void loadStats();
    void loadRecords();
  });

  function syncFromUrl() {
    const params = $page.url.searchParams;
    q = params.get('q') ?? '';
    selectedLabels = params.get('labels')?.split(',').filter(Boolean) ?? [];
    hasEntities = params.get('has_entities') ?? '';
    sort = (params.get('sort') as RecordSort) ?? 'created_at_desc';
    pageNumber = Number(params.get('page') ?? '1') || 1;
  }

  async function loadDataset() {
    dataset = await api.getDataset(datasetId);
  }

  async function loadStats() {
    stats = await api.getStats(datasetId);
  }

  async function loadRecords() {
    loading = true;
    error = '';
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (selectedLabels.length) params.set('labels', selectedLabels.join(','));
      if (hasEntities) params.set('has_entities', hasEntities);
      params.set('sort', sort);
      params.set('page', String(pageNumber));
      params.set('page_size', String(pageSize));
      const response = await api.listRecords(datasetId, `?${params}`);
      records = response.items;
      total = response.total;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Не удалось загрузить записи';
    } finally {
      loading = false;
    }
  }

  async function applyFilters(resetPage = true) {
    if (resetPage) pageNumber = 1;
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (selectedLabels.length) params.set('labels', selectedLabels.join(','));
    if (hasEntities) params.set('has_entities', hasEntities);
    params.set('sort', sort);
    params.set('page', String(pageNumber));
    await goto(`?${params}`, { keepFocus: true, noScroll: true });
    await loadRecords();
  }

  function toggleLabel(label: string) {
    selectedLabels = selectedLabels.includes(label)
      ? selectedLabels.filter((item) => item !== label)
      : [...selectedLabels, label];
    void applyFilters();
  }

  async function changePage(delta: number) {
    const next = Math.min(totalPages, Math.max(1, pageNumber + delta));
    if (next === pageNumber) return;
    pageNumber = next;
    await applyFilters(false);
  }

  async function createRecord() {
    if (!text.trim()) return;
    await api.createRecord(datasetId, { text });
    text = '';
    await Promise.all([loadRecords(), loadStats(), loadDataset()]);
  }

  async function renameDataset() {
    if (!dataset) return;
    const name = prompt('Новое название', dataset.name);
    if (!name) return;
    dataset = await api.updateDataset(datasetId, { name });
  }

  async function uploadJsonl() {
    if (!file) return;
    error = '';
    importJob = await api.importJsonl(datasetId, file, duplicateMode);
    void pollImport(importJob.id);
  }

  async function pollImport(jobId: string) {
    const job = await api.getImportJob(datasetId, jobId);
    importJob = job;
    if (job.status === 'pending' || job.status === 'running') {
      setTimeout(() => pollImport(jobId), 2000);
    } else {
      await Promise.all([loadRecords(), loadStats(), loadDataset()]);
    }
  }
</script>

<section class="grid">
  <p><a href="/">← К датасетам</a></p>

  <div class="card">
    <div class="row wrap" style="justify-content: space-between">
      <div>
        <h1>{dataset?.name ?? 'Датасет'}</h1>
        {#if dataset?.description}
          <p class="muted">{dataset.description}</p>
        {/if}
        <p class="muted">Записей: {dataset?.records_count ?? total}</p>
      </div>
      <button class="secondary" type="button" on:click={renameDataset}>Переименовать</button>
    </div>

    {#if stats && availableLabels.length}
      <div class="row wrap">
        {#each availableLabels as label}
          <span class="tag">{label}: {stats.labels[label]}</span>
        {/each}
      </div>
    {/if}
  </div>

  <form class="card grid" on:submit|preventDefault={createRecord}>
    <h2>Добавить запись</h2>
    <textarea bind:value={text} placeholder="Текст записи"></textarea>
    <button type="submit">Добавить</button>
  </form>

  <div class="card grid">
    <h2>Импорт JSONL</h2>
    <div class="row wrap">
      <input type="file" accept=".jsonl" on:change={(event) => (file = event.currentTarget.files?.[0] ?? null)} />
      <select bind:value={duplicateMode}>
        <option value="skip">Дубликаты: пропускать</option>
        <option value="overwrite">Дубликаты: перезаписывать</option>
      </select>
      <button type="button" on:click={uploadJsonl}>Импортировать</button>
    </div>
    {#if importJob}
      <p class="muted">
        Статус: {importJob.status}, загружено: {importJob.loaded_count}, пропущено: {importJob.skipped_count},
        ошибок: {importJob.error_count}
      </p>
    {/if}
  </div>

  <div class="card grid">
    <h2>Экспорт</h2>
    <div class="row wrap">
      {#each exportFormats as format}
        <a class="tag" href={api.exportUrl(datasetId, format.value, currentFilters)}>{format.label}</a>
      {/each}
    </div>
    <p class="muted">Экспортируется текущий фильтр.</p>
  </div>

  <div class="card grid">
    <h2>Фильтры</h2>
    <form class="row wrap" on:submit|preventDefault={() => applyFilters()}>
      <input bind:value={q} placeholder="Поиск по тексту" />
      <select bind:value={hasEntities} on:change={() => applyFilters()}>
        <option value="">Сущности: любые</option>
        <option value="true">Есть сущности</option>
        <option value="false">Нет сущностей</option>
      </select>
      <select bind:value={sort} on:change={() => applyFilters()}>
        <option value="created_at_desc">Сначала новые</option>
        <option value="created_at_asc">Сначала старые</option>
        <option value="text_length_desc">По длине текста</option>
      </select>
      <button type="submit">Искать</button>
    </form>

    {#if availableLabels.length}
      <div class="row wrap">
        {#each availableLabels as label}
          <button
            type="button"
            class={selectedLabels.includes(label) ? '' : 'secondary'}
            on:click={() => toggleLabel(label)}
          >
            {label}
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="card grid">
    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="row wrap" style="justify-content: space-between">
      <h2>Записи ({total})</h2>
      <div class="row">
        <button class="secondary" type="button" disabled={pageNumber <= 1} on:click={() => changePage(-1)}>
          ←
        </button>
        <span class="muted">{pageNumber} / {totalPages}</span>
        <button class="secondary" type="button" disabled={pageNumber >= totalPages} on:click={() => changePage(1)}>
          →
        </button>
      </div>
    </div>

    {#if loading}
      <p class="muted">Загрузка...</p>
    {:else if records.length === 0}
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
