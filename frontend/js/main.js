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
document.addEventListener("DOMContentLoaded", async function() {
    
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

            // [关键逻辑]
            // 1. 如果 data.sentiment_index 是 null，说明后端只完成了阶段1 (只有新闻)
            //    我们返回 false，让 pollForNews 继续轮询，等待阶段2 (分析) 完成。
            // 2. 如果 data.sentiment_index 有值，说明阶段2完成，返回 true 停止轮询。
            
            if (data && data.sentiment_index === null) {
                // console.log(">>> [News] 只有新闻，等待 NLP...");
                return false; // 继续轮询
            }
            return true; // 这里的 true 意味着“彻底完成”，停止轮询
        } catch (e) {
            // 503 错误等
            return false; // 继续轮询
        }
    }

    // 轮询加载新闻数据的函数
    async function pollForNews(retries = 60, delay = 1000) {
        // 尝试 30次 * 2秒 = 60秒 (足够 NLP 跑完了)
        // 先渲染一个“正在分析”的状态
        renderLoading(newsContent, "正在进行 AI 舆情分析...");
        
        for (let i = 0; i < retries; i++) {
            const success = await loadNews();
            if (success) {
                console.log("News data loaded successfully.");
                return; // 加载成功，退出
            }
            await new Promise(r => setTimeout(r, delay));
        }
        renderError(newsContent, "新闻加载超时");
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
            return true;
        } catch (e) {
            console.warn("SPDR Gold data not ready.") // 捕获 503 等错误
            return false;
        }
    }

    // 轮询加载 SPDR 黄金数据的函数
    async function pollForSPDRGold(retries = 30, delay = 6000) {
        for (let i = 0; i < retries; i++) {
            const success = await loadSPDRGold();
            if (success) {
                console.log("SPDR Gold data loaded successfully.");
                return;
            }
            await new Promise(res => setTimeout(res, delay));
        }
        console.error("Failed to load SPDR Gold data after multiple attempts.");
        renderSPDRGold("N/A"); // 显示加载失败
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
    loadAI();
    loadGlobal();
    loadDomestic();
    loadIndicators();
    console.log("Starting to poll for news data...");
    await pollForNews();
    console.log("Starting to poll for SPDR Gold data...");
    pollForSPDRGold();

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