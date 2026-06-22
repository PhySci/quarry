<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Dataset } from '$lib/api';

  let datasets: Dataset[] = [];
  let name = '';
  let description = '';
  let error = '';
  let loading = true;

  onMount(loadDatasets);

  async function loadDatasets() {
    loading = true;
    error = '';
    try {
      datasets = await api.listDatasets();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Не удалось загрузить датасеты';
    } finally {
      loading = false;
    }
  }

  async function createDataset() {
    if (!name.trim()) return;
    const dataset = await api.createDataset({ name, description });
    datasets = [dataset, ...datasets];
    name = '';
    description = '';
  }

  async function deleteDataset(id: string) {
    await api.deleteDataset(id);
    datasets = datasets.filter((dataset) => dataset.id !== id);
  }
</script>

<section class="grid">
  <div>
    <h1>NER Dataset Manager</h1>
    <p class="muted">Управление датасетами, записями и NER-сущностями.</p>
  </div>

  <form class="card grid" on:submit|preventDefault={createDataset}>
    <h2>Новый датасет</h2>
    <input bind:value={name} placeholder="Название" />
    <input bind:value={description} placeholder="Описание" />
    <button type="submit">Создать</button>
  </form>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="card">
    <h2>Датасеты</h2>
    {#if loading}
      <p class="muted">Загрузка...</p>
    {:else if datasets.length === 0}
      <p class="muted">Пока нет датасетов.</p>
    {:else}
      <table>
        <thead>
          <tr>
            <th>Название</th>
            <th>Записей</th>
            <th>Обновлён</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each datasets as dataset}
            <tr>
              <td>
                <a href={`/datasets/${dataset.id}`}>{dataset.name}</a>
                {#if dataset.description}
                  <div class="muted">{dataset.description}</div>
                {/if}
              </td>
              <td>{dataset.records_count}</td>
              <td>{new Date(dataset.updated_at).toLocaleString()}</td>
              <td>
                <button class="danger" type="button" on:click={() => deleteDataset(dataset.id)}>Удалить</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</section>
