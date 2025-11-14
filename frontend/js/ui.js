// --- 1. 实时报价 ---
export function renderRealtimeQuote(element, data) {
    if (!data) {
        element.innerHTML = '<div class="placeholder">实时价格加载失败...</div>';
        return;
    }
    element.innerHTML = `
        <div class="realtime-price">${data.price.toFixed(2)} CNY</div>
        <div class="realtime-time">SGE 时间: ${data.time}</div>
        <div class="realtime-time">最后更新: ${data.update_time}</div>
    `;
}

// --- 2. AI 预测 ---
export function renderAIPrediction(element, apiResponse) {
    let signalColor = '#333';
    if (apiResponse.signal === '看涨' || apiResponse.signal === '多头趋势') { signalColor = '#ff4d4f'; }
    else if (apiResponse.signal === '看跌' || apiResponse.signal === '空头趋势') { signalColor = '#52c41a'; }
    else if (apiResponse.signal === '震荡') { signalColor = '#faad14'; }
    
    element.innerHTML = `
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="font-size: 1.8rem; font-weight: bold; color: ${signalColor};">
                ${apiResponse.signal}
            </div>
        </div>
        <div style="font-size: 0.9rem; color: #888; line-height: 1.4;">
            <strong>分析:</strong> ${apiResponse.detail}
        </div>`;
}

// --- 3. 新闻快讯 ---
function formatNewsTime(isoString) {
    try {
        const date = new Date(isoString);
        const y = date.getFullYear(); const m = (date.getMonth() + 1).toString().padStart(2, '0');
        const d = date.getDate().toString().padStart(2, '0'); const h = date.getHours().toString().padStart(2, '0');
        const min = date.getMinutes().toString().padStart(2, '0');
        return `${y}-${m}-${d} ${h}:${min}`;
    } catch(e) { return isoString; }
}

export function renderNewsData(element, data) {
    if (!data || data.length === 0) {
        element.innerHTML = '<div class="placeholder">暂无新闻。</div>';
        return;
    }
    data.reverse(); 
    let html = '';
    data.forEach(item => {
        const formattedTime = formatNewsTime(item.report_time);
        let title = ''; let content = item.report_content;
        if (content.startsWith('【') && content.includes('】')) {
            const splitIndex = content.indexOf('】') + 1;
            title = content.substring(0, splitIndex); content = content.substring(splitIndex);
        }
        html += `<div class="news-item"><div class="news-time">${formattedTime}</div><div class="news-title">${title}</div><div class="news-content">${content}</div></div>`;
    });
    element.innerHTML = html;
}

// --- 4. 全球市场 ---
function renderMarketItem(name, data) {
    if (typeof data.price !== 'number' || typeof data.change_pct !== 'number') {
         return `<div class="global-market-item"><span class="name">${name}</span> <span class="price">数据获取失败</span></div>`;
    }
    let price = parseFloat(data.price);
    let change = parseFloat(data.change_pct);
    let changeClass = 'change-flat';
    if (change > 0) changeClass = 'change-up';
    else if (change < 0) changeClass = 'change-down';
    return `
        <div class="global-market-item">
            <span class="name">${name}</span>
            <div>
                <span class="price">${price.toFixed(2)}</span>
                <span class="change ${changeClass}">
                    ${(change > 0 ? '+' : '') + change.toFixed(2)}%
                </span>
            </div>
        </div>`;
}
export function renderGlobalMarkets(element, data) {
    if (!data) {
        element.innerHTML = '<div class="placeholder">暂无数据。</div>';
        return;
    }
    let html = '';
    html += renderMarketItem('国际黄金 (XAU/USD)', data.xau_usd);
    html += renderMarketItem('美元指数 (DXY)', data.dxy);
    html += renderMarketItem('美债10年 (US 10Y)', data.us_10y);
    element.innerHTML = html;
}

// --- 5. 国内宏观 ---
function renderMacroItem(name, value, unit = '%', digits = 1) {
    if (typeof value !== 'number') {
        return `<div class="macro-item"><span class="name">${name}</span> <span class="value">N/A</span></div>`;
    }
    let valueColor = '#333';
    if (name.includes('月增')) {
        if (value > 0) valueColor = '#ff4d4f'; 
        else if (value < 0) valueColor = '#52c41a';
    } else if (unit === '%') {
        if (value > 0) valueColor = '#ff4d4f'; 
        else if (value < 0) valueColor = '#52c41a';
    }
    return `
        <div class="macro-item">
            <span class="name">${name}</span>
            <span class="value" style="color: ${valueColor};">
                ${value.toFixed(digits)}${unit}
            </span>
        </div>`;
}
export function renderDomesticMacro(element, data) {
    if (!data) {
        element.innerHTML = '<div class="placeholder">暂无数据。</div>';
        return;
    }
    let html = '';
    html += renderMacroItem('CPI 同比', data.cpi_yoy);
    html += renderMacroItem('PPI 同比', data.ppi_yoy);
    html += renderMacroItem('M2 同比', data.m2_yoy);
    html += renderMacroItem('GDP 同比', data.gdp_yoy);
    html += renderMacroItem('央行购金-月增', data.pboc_gold_buy, '万盎司', 2);
    element.innerHTML = html;
}

// --- 7. 错误/加载状态 ---
export function renderLoading(element, text = '正在加载...') {
    element.innerHTML = `<div class="placeholder">${text}</div>`;
}
export function renderError(element, text = '加载失败') {
    element.innerHTML = `<div class="placeholder" style="color: #ff4d4f;">${text}</div>`;
}