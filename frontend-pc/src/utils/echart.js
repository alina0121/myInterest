import * as echarts from 'echarts'

/** 简易 ECharts 生命周期绑定：自动 init/resize/dispose */
export function useEchart(elRef, optionRef) {
  let chart = null
  let ro = null

  function render() {
    if (!elRef.value) return
    if (!chart) {
      chart = echarts.init(elRef.value)
      ro = new ResizeObserver(() => chart && chart.resize())
      ro.observe(elRef.value)
    }
    chart.setOption(optionRef.value, true)
  }

  function dispose() {
    ro && ro.disconnect()
    chart && chart.dispose()
    chart = null
  }

  return { render, dispose }
}
