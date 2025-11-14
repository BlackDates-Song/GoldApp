const API_BASE_URL = "";

async function fetchData(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP 错误! 状态: ${response.status}`);
        }
        const apiResponse = await response.json();
        if (!apiResponse.success) {
            throw new Error(`API 错误: ${apiResponse.detail || '未知错误'}`);
        }
        return apiResponse.data;
    } catch (error) {
        console.error(`[API] ${endpoint} 加载失败:`, error);
        throw error; // 将错误抛出, 由调用者处理
    }
}

export const fetchKLineData = (period) => fetchData(`/api/gold-data?period=${period}`);
export const fetchIntradayData = () => fetchData(`/api/gold-intraday`);
export const fetchRealtimeQuote = () => fetchData(`/api/gold-realtime-quote`); // (这个API结构不同, 单独处理)
export const fetchAIPrediction = () => fetchData(`/api/ai-prediction`); // (这个API结构不同, 单独处理)
export const fetchNewsData = () => fetchData(`/api/gold-news`);
export const fetchGlobalMarkets = () => fetchData(`/api/global-markets`);
export const fetchDomesticMacro = () => fetchData(`/api/domestic-macro`);
export const fetchMarketIndicators = () => fetchData(`/api/market-indicators`);

export async function getRealtimeQuote() {
     try {
        const response = await fetch(`${API_BASE_URL}/api/gold-realtime-quote`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        if (data.success) {
            return data;
        }
        throw new Error('API success field was false');
    } catch (error) {
        console.error(`[API] /api/gold-realtime-quote 加载失败:`, error);
        return null; // 静默处理
    }
}

export async function getAIPrediction() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai-prediction`);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.error(`[API] /api/ai-prediction 加载失败:`, error);
        throw error;
    }
}