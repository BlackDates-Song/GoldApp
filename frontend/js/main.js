// frontend/js/main.js

// 1. 从其他模块导入
import { 
    fetchNewsData, 
    fetchGlobalMarkets, 
    fetchDomesticMacro, 
    fetchMarketIndicators,
    fetchSpdrGold,
    getRealtimeQuote,
    getAIPrediction
} from './api.js';

import {
    renderRealtimeQuote,
    renderAIPrediction,
    renderNewsData,
    renderGlobalMarkets,
    renderDomesticMacro,
    renderMarketIndicators,
    renderSPDRGold,
    renderLoading,
    renderError
} from './ui.js';

import { 
    loadKLineData, 
    loadIntradayData 
} from './chart.js';

// 2. DOMContentLoaded 事件, 确保页面已加载
document.addEventListener("DOMContentLoaded", function() {
    
    // 3. 初始化图表和获取 DOM 元素
    const chartContainer = document.getElementById('chart-container');
    const myChart = window.echarts.init(chartContainer);
    
    const quoteContent = document.getElementById('realtime-content');
    const newsContent = document.getElementById('news-content');
    const aiContent = document.getElementById('ai-content');
    const marketsContent = document.getElementById('global-markets-content');
    const domesticMacroContent = document.getElementById('domestic-macro-content');
    const marketIndicatorsContent = document.getElementById('market-indicators-content');

    // 4. 封装的加载函数
    async function loadQuote() {
        const data = await getRealtimeQuote();
        if (data) {
            renderRealtimeQuote(quoteContent, data);
        }
    }

    async function loadAI() {
        try {
            const data = await getAIPrediction();
            renderAIPrediction(aiContent, data);
        } catch (e) {
            renderError(aiContent, 'AI 分析加载失败');
        }
    }

    async function loadNews() {
        try {
            const data = await fetchNewsData();
            renderNewsData(newsContent, data);
        } catch (e) {
            renderError(newsContent, '新闻加载失败');
        }
    }

    async function loadGlobal() {
        try {
            const data = await fetchGlobalMarkets();
            renderGlobalMarkets(marketsContent, data);
        } catch (e) {
            renderError(marketsContent, '全球市场加载失败');
        }
    }

    async function loadDomestic() {
        try {
            const data = await fetchDomesticMacro();
            renderDomesticMacro(domesticMacroContent, data);
        } catch (e) {
            renderError(domesticMacroContent, '国内宏观加载失败');
        }
    }

    async function loadIndicators() {
        try {
            const data = await fetchMarketIndicators();
            renderMarketIndicators(marketIndicatorsContent, data);
        } catch (e) {
            renderError(marketIndicatorsContent, '市场指标加载失败');
        }
    }

    async function loadSPDRGold() {
        try {
            const data = await fetchSpdrGold();
            // 仅更新 SPDR 黄金的 <span> 占位符
            renderSPDRGold(data); 
        } catch (e) {
            renderSPDRGold("N/A"); // 捕获 503 等错误
        }
    }

    // 5. 绑定按钮事件
    const controlButtons = document.querySelectorAll('.k-line-button');
    controlButtons.forEach(button => {
        button.addEventListener('click', () => {
            const type = button.dataset.type; 
            controlButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            if (type === 'intraday') { 
                loadIntradayData(myChart, true); // true = 显示加载动画
            } 
            else if (type === 'kline') { 
                loadKLineData(myChart, button.dataset.period); 
            }
        });
    });

    // 6. 初始加载
    loadIntradayData(myChart, true); 
    loadQuote();
    loadNews();
    loadAI();
    loadGlobal();
    loadDomestic();
    loadIndicators();
    loadSPDRGold();

    // 7. 设置定时器
    setInterval(loadQuote, 10000); 
    setInterval(() => {
        // 只有在分时图激活时才刷新
        if (document.querySelector('.k-line-button[data-type="intraday"].active')) {
            loadIntradayData(myChart, false); // false = 不显示加载动画
        }
    }, 10 * 1000);
    
    setInterval(loadNews, 15 * 60 * 1000); 
    setInterval(loadAI, 15 * 60 * 1000); 
    setInterval(loadGlobal, 15 * 60 * 1000); 
    setInterval(loadIndicators, 4 * 60 * 60 * 1000); // 4 小时
    setInterval(loadDomestic, 24 * 60 * 60 * 1000); // 24 小时
    setInterval(loadSPDRGold, 12 * 60 * 60 * 1000); // 12 小时
    
    // 8. 窗口大小调整
    window.addEventListener('resize', () => myChart.resize());
});