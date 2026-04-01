/**
 * 全局巡检数据存储（简易响应式 store，不依赖 Pinia）
 * 用于在检测工作台和报告页之间共享数据
 */
import { reactive } from 'vue'

export const inspectionStore = reactive({
  // 本次巡检的所有结果（有缺陷的图）
  defectRecords: [],

  // 添加一条记录
  addRecord(record) {
    this.defectRecords.push(record)
  },

  // 清空（开始新一次巡检时调用）
  clear() {
    this.defectRecords = []
  },

  // 统计
  get totalDefects() {
    return this.defectRecords.reduce((sum, r) => sum + r.detections.length, 0)
  },
  get highDangerCount() {
    return this.defectRecords.reduce((sum, r) => {
      return sum + r.detections.filter(d => d.danger_level === '高').length
    }, 0)
  },
  get totalCost() {
    return this.defectRecords.reduce((sum, r) => {
      return sum + r.detections.reduce((s, d) => s + d.estimated_cost, 0)
    }, 0)
  },
})
