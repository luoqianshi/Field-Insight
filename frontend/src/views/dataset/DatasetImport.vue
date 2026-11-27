<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { datasetsApi, type ScanResult } from '@/api/datasets'

const router = useRouter()

const importPath = ref('')
const scanResult = ref<ScanResult | null>(null)
const importName = ref('')
const importDesc = ref('')
const scanning = ref(false)
const importing = ref(false)
const scanError = ref('')
const importError = ref('')

async function pickFolder() {
  try {
    const res = await datasetsApi.pickFolder()
    if (res.data.path) importPath.value = res.data.path
  } catch (e: any) {
    scanError.value = e.message || '选择文件夹失败'
  }
}

async function doScan() {
  scanError.value = ''
  scanResult.value = null
  if (!importPath.value) { scanError.value = '请输入数据集目录路径'; return }
  scanning.value = true
  try {
    const res = await datasetsApi.scan(importPath.value)
    scanResult.value = res.data
  } catch (e: any) {
    scanError.value = e.response?.data?.message || e.message || '扫描失败'
  } finally {
    scanning.value = false
  }
}

async function doImport() {
  importError.value = ''
  if (!scanResult.value?.valid) { importError.value = '请先扫描并确认数据集'; return }
  importing.value = true
  try {
    const res = await datasetsApi.import(importPath.value, importName.value || undefined, importDesc.value || undefined)
    router.push(`/dataset/datasets/${res.data.dataset_id}`)
  } catch (e: any) {
    importError.value = e.response?.data?.message || e.message || '导入失败'
  } finally {
    importing.value = false
  }
}

// 格式标签样式
function formatTagStyle(fmt: string) {
  if (fmt === 'YOLO') return { cls: 'tag tag-blue', style: '' }
  if (fmt === 'COCO') return { cls: 'tag', style: 'background:#FEF3C7;color:#B45309;' }
  if (fmt === 'VOC') return { cls: 'tag', style: 'background:#F3E8FF;color:#7E22CE;' }
  return { cls: 'tag', style: '' }
}
</script>

<template>
  <AppLayout>
    <!-- 面包屑 -->
    <div class="flex items-center gap-1 text-xs text-ink-tertiary mb-2">
      <router-link to="/dataset/datasets" class="hover:text-brand-700">数据集</router-link>
      <i class="fa-solid fa-chevron-right text-[8px]"></i>
      <span class="text-ink-primary">载入数据集</span>
    </div>
    <h1 class="text-2xl font-semibold text-ink-primary mb-1">载入数据集</h1>
    <p class="text-sm text-ink-secondary mb-6">扫描并载入已标注完备的数据集（COCO / YOLO / VOC）· 单个数据集仅管理一种标注格式</p>

    <div class="grid grid-cols-3 gap-5">
      <div class="col-span-2 space-y-5">
        <div class="bg-white border border-surface-border rounded-card p-6">
          <h2 class="text-base font-semibold text-ink-primary mb-4">■ 数据集路径</h2>
          <div class="flex gap-2 mb-3">
            <input v-model="importPath" type="text" placeholder="如 datasets/SSDC-UAV_COCO 或绝对路径"
              class="flex-1 px-3 py-2 bg-white border border-surface-border rounded-btn text-sm font-mono focus:outline-none focus:border-brand-300" />
            <button @click="pickFolder" class="px-3 py-2 bg-white border border-surface-border hover:bg-surface-hover rounded-btn text-sm text-ink-secondary">
              <i class="fa-solid fa-folder-open"></i> 选择
            </button>
            <button @click="doScan" :disabled="scanning"
              class="px-4 py-2 bg-brand-700 hover:bg-brand-900 disabled:opacity-50 text-white rounded-btn text-sm font-medium">
              {{ scanning ? '扫描中…' : '扫描预检' }}
            </button>
          </div>
          <div v-if="scanError" class="mb-3 text-xs text-red-600 flex items-center gap-1.5">
            <i class="fa-solid fa-circle-exclamation"></i>{{ scanError }}
          </div>
          <!-- 预检结果 -->
          <div v-if="scanResult && scanResult.valid" class="bg-brand-50/50 border border-brand-100 rounded-btn p-4">
            <div class="flex items-center gap-2 mb-3">
              <i class="fa-solid fa-circle-check text-brand-700"></i>
              <span class="text-sm font-medium text-ink-primary">{{ scanResult.message }}</span>
              <span :class="formatTagStyle(scanResult.format!).cls" :style="formatTagStyle(scanResult.format!).style">{{ scanResult.format }}</span>
            </div>
            <div class="grid grid-cols-4 gap-3 text-xs">
              <div><div class="text-ink-tertiary">图片数</div><div class="text-ink-primary font-semibold mt-0.5">{{ scanResult.image_count.toLocaleString() }}</div></div>
              <div><div class="text-ink-tertiary">标注框数</div><div class="text-ink-primary font-semibold mt-0.5">{{ scanResult.object_count.toLocaleString() }}</div></div>
              <div><div class="text-ink-tertiary">原图数</div><div class="text-ink-primary font-semibold mt-0.5">{{ scanResult.origin_image_count }}</div></div>
              <div><div class="text-ink-tertiary">分辨率</div><div class="text-ink-primary font-semibold mt-0.5">{{ scanResult.image_size }}</div></div>
            </div>
            <div class="mt-2 text-xs text-ink-tertiary">类别：{{ scanResult.classes.join('、') }}</div>
          </div>
        </div>
        <div class="bg-white border border-surface-border rounded-card p-6">
          <h2 class="text-base font-semibold text-ink-primary mb-4">■ 导入选项（可选）</h2>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-ink-primary mb-1.5">数据集名称（留空用推断名）</label>
              <input v-model="importName" type="text" class="w-full px-3 py-2 bg-white border border-surface-border rounded-btn text-sm font-mono focus:outline-none focus:border-brand-300" />
            </div>
            <div>
              <label class="block text-xs font-medium text-ink-primary mb-1.5">描述</label>
              <textarea v-model="importDesc" rows="2" class="w-full px-3 py-2 bg-white border border-surface-border rounded-btn text-sm focus:outline-none focus:border-brand-300 resize-none"></textarea>
            </div>
          </div>
        </div>
      </div>
      <div class="space-y-5">
        <div class="bg-white border border-surface-border rounded-card p-5 sticky top-5">
          <h3 class="text-sm font-semibold text-ink-primary mb-3">导入摘要</h3>
          <div class="space-y-2.5 text-xs">
            <div class="flex justify-between"><span class="text-ink-tertiary">路径</span><span class="font-mono text-[11px] text-right">{{ importPath || '—' }}</span></div>
            <div class="flex justify-between"><span class="text-ink-tertiary">格式</span><span class="text-ink-primary">{{ scanResult?.format || '—' }}</span></div>
            <div class="flex justify-between"><span class="text-ink-tertiary">图片数</span><span class="text-ink-primary">{{ scanResult?.image_count || 0 }}</span></div>
          </div>
          <div v-if="importError" class="mt-3 text-xs text-red-600">{{ importError }}</div>
          <button @click="doImport" :disabled="importing || !scanResult?.valid"
            class="mt-4 w-full px-3 py-2 bg-brand-700 hover:bg-brand-900 disabled:opacity-50 text-white rounded-btn text-sm font-medium">
            {{ importing ? '导入中…' : '确认导入' }}
          </button>
          <router-link to="/dataset/datasets" class="mt-2 block text-center text-xs text-ink-tertiary hover:text-brand-700">取消</router-link>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
