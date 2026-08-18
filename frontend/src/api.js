const API_BASE_URL = 'http://localhost:8000/api/v1';

export const createQuery = async (topic) => {
    // We are hardcoding user_id=1 for the MVP, as per the plan
    const response = await fetch(`${API_BASE_URL}/queries/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            topic,
            user_id: 1,
        }),
    });
    
    if (!response.ok) {
        throw new Error('Failed to create research query');
    }
    
    return response.json();
};

export const subscribeToQueryEvents = (queryId, onMessage) => {
    const eventSource = new EventSource(`${API_BASE_URL}/queries/${queryId}/stream`);
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
            if (data.status === 'completed' || data.status === 'failed') {
                eventSource.close();
            }
        } catch (err) {
            console.error('Error parsing SSE event:', err);
        }
    };
    
    eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        eventSource.close();
        onMessage({ status: 'failed', message: 'Connection lost' });
    };
    
    return eventSource;
};
