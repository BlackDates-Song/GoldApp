import { fetchKLineData, fetchIntradayData } from './api.js';

// --- 1. 图表模板 ---
const kLineOptionTemplate = {
    tooltip: { 
        trigger: 'axis', 
        axisPointer: { type: 'cross' },
        formatter: function (params) {
            let date = params[0].name; let tooltipHtml = `${date}<br/>`; 
            params.forEach(param => {
                let seriesName = param.seriesName; let color = param.color; let value = param.value;
                let marker = `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>`;
                if (seriesName === 'K线') {
                    tooltipHtml += `${marker} <strong>${seriesName}</strong><br/>`;
                    tooltipHtml += `  开盘价: <strong>${value[1]}</strong><br/>`;
                    tooltipHtml += `  收盘价: <strong>${value[2]}</strong><br/>`;
                    tooltipHtml += `  最低价: <strong>${value[3]}</strong><br/>`;
                    tooltipHtml += `  最高价: <strong>${value[4]}</strong><br/>`;
                } else if (seriesName.startsWith('MA')) {
                    if (value !== null && value !== undefined) { 
                         tooltipHtml += `${marker} ${seriesName}: <strong>${value}</strong><br/>`;
                    }
                }
            });
            return tooltipHtml;
        }
    },
    legend: { data: ['K线', 'MA5', 'MA10', 'MA20'], top: 0 },
    grid: [ { left: '20px', right: '20px', height: '65%', containLabel: true } ],
    xAxis: [ { type: 'category', data: [], gridIndex: 0, scale: true } ],
    yAxis: [ { type: 'value', gridIndex: 0, scale: true, splitLine: { show: true }, axisLabel: { formatter: '{value} CNY' } } ],
    dataZoom: [ 
        { type: 'inside', xAxisIndex: [0] }, 
        { type: 'slider', xAxisIndex: [0], top: '85%' } 
    ],
    series: [ 
        { 
            name: 'K线', type: 'candlestick', 
            xAxisIndex: 0, yAxisIndex: 0, data: [],
            markPoint: { data: [ { type: 'max', valueDim: 'highest' }, { type: 'min', valueDim: 'lowest' } ] }
        },
        { name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: [], smooth: true, showSymbol: false, lineStyle: { width: 1, opacity: 0.8 } },
        { name: 'MA10', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: [], smooth: true, showSymbol: false, lineStyle: { width: 1, opacity: 0.8 } },
        { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: [], smooth: true, showSymbol: false, lineStyle: { width: 1, opacity: 0.8 } }
    ]
};

const intradayOptionTemplate = {
    tooltip: { 
        trigger: 'axis',
        formatter: function (params) {
            var param = params[0]; if (!param || param.value === '-' || param.value === null) { return null; }
            return param.name + '<br />价格: ' + param.value;
        }
    },
    grid: [ { left: '20px', right: '20px', height: '65%', containLabel: true } ],
    xAxis: [ { type: 'category', data: [], scale: true, boundaryGap: false } ],
    yAxis: [ { type: 'value', scale: true, axisLabel: { formatter: '{value} CNY' } } ],
    dataZoom: [ { type: 'inside', xAxisIndex: [0], start: 0, end: 100 }, { type: 'slider', xAxisIndex: [0], top: '85%', start: 0, end: 100 } ],
    series: [ { name: '价格', type: 'line', showSymbol: false, smooth: true, data: [], connectNulls: false,
            markPoint: { data: [ { type: 'max', name: '最高价' }, { type: 'min', name: '最低价' } ] }
        }
    ]
};

// --- 2. 图表加载逻辑 ---
export async function loadKLineData(myChart, period) {
    myChart.showLoading(); 
    try {
        const apiResponse = await fetchKLineData(period);
        
        let kLineData = apiResponse.k_line_data.map(item => [item[1], item[2], item[3], item[4]]);
        
        const windowSize = 15;
        const endIndex = apiResponse.dates.length - 1;
        const startIndex = Math.max(0, endIndex - (windowSize - 1)); 
        const startValue = apiResponse.dates[startIndex];
        const endValue = apiResponse.dates[endIndex];
        
        myChart.setOption(kLineOptionTemplate, true); 
        
        myChart.setOption({
            xAxis: [ { data: apiResponse.dates } ],
            series: [ 
                { name: 'K线', data: kLineData },
                { name: 'MA5', data: apiResponse.ma5 },
                { name: 'MA10', data: apiResponse.ma10 },
                { name: 'MA20', data: apiResponse.ma20 }
            ],
            dataZoom: [ 
                { type: 'inside', startValue: startValue, endValue: endValue }, 
                { type: 'slider', top: '85%', startValue: startValue, endValue: endValue }
            ]
        });
        
        myChart.hideLoading(); 
    } catch (error) { 
        myChart.showLoading({ text: `K线数据加载失败`, showSpinner: false }); 
    }
} 

export async function loadIntradayData(myChart, showAnimation = true) {
    if (showAnimation) {
        myChart.showLoading(); 
    }
    try {
        const apiResponse = await fetchIntradayData();
        
        if (apiResponse.length === 0) {
             if (showAnimation) {
                myChart.showLoading({ text: `当前休市中...`, showSpinner: false });
             }
             return;
        }

        const axisLabels = []; const seriesValues = []; 
        const GAP_THRESHOLD_MINUTES = 60; let lastTime = 0;
        for (let i = 0; i < apiResponse.length; i++) {
            const point = apiResponse[i]; 
            const currentTime = new Date(point[0]).getTime();
            const value = point[1];
            if (i > 0) {
                const gapInMinutes = (currentTime - lastTime) / (1000 * 60);
                if (gapInMinutes > GAP_THRESHOLD_MINUTES) { axisLabels.push(''); seriesValues.push('-'); }
            }
            var date = new Date(currentTime);
            var timeLabel = [date.getHours(), date.getMinutes()].map(function (n) { return n < 10 ? '0' + n : n; }).join(':');
            axisLabels.push(timeLabel); seriesValues.push(value); lastTime = currentTime;     
        }
        
        if (showAnimation) {
            myChart.clear();
            myChart.setOption(intradayOptionTemplate, true);
        }
        
        myChart.setOption({ 
            xAxis: [ { data: axisLabels } ], 
            series: [ { data: seriesValues } ] 
        });

        if (showAnimation) {
            myChart.hideLoading();
        }
    } catch (error) { 
        console.error("分时图加载失败:", error); 
        if (showAnimation) {
            myChart.showLoading({ text: `分时数据加载失败`, showSpinner: false }); 
        }
    }
}