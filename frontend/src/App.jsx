import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { createQuery, subscribeToQueryEvents } from './api';

function App() {
  const [topic, setTopic] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [events, setEvents] = useState([]);
  const [finalReport, setFinalReport] = useState('');
  const eventSourceRef = useRef(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    // Reset state
    setEvents([]);
    setFinalReport('');
    setIsResearching(true);

    if (eventSourceRef.current) {
        eventSourceRef.current.close();
    }

    try {
      // 1. Create Query
      const query = await createQuery(topic);

      // 2. Subscribe to SSE
      eventSourceRef.current = subscribeToQueryEvents(query.id, (data) => {
        setEvents((prev) => [...prev, data]);
        
        if (data.status === 'completed') {
            setIsResearching(false);
            if (data.result) {
                setFinalReport(data.result);
            }
        } else if (data.status === 'failed') {
            setIsResearching(false);
        }
      });
    } catch (err) {
      console.error(err);
      setIsResearching(false);
      setEvents([{ status: 'failed', message: 'Failed to start research.' }]);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }
    };
  }, []);

  return (
    <>
      <header>
        <h1>Agentic AI Researcher</h1>
        <p className="subtitle">Powered by LangGraph and Gemini</p>
      </header>

      <form className="search-container" onSubmit={handleSearch}>
        <input 
          type="text" 
          className="search-input" 
          placeholder="Enter a research topic (e.g., Quantum Computing advancements)..." 
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={isResearching}
        />
        <button type="submit" className="btn-primary" disabled={isResearching || !topic.trim()}>
          {isResearching ? 'Researching...' : 'Start Research'}
        </button>
      </form>

      {events.length > 0 && (
        <div className="content-grid">
            <div className="timeline-container">
                <div className="glass-panel timeline">
                    <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--primary)' }}>Agent Actions</h3>
                    {events.map((evt, idx) => (
                        <div 
                            key={idx} 
                            className={`timeline-item ${evt.status === 'completed' ? 'completed' : evt.status === 'failed' ? 'failed' : ''}`}
                        >
                            <div className="timeline-meta">
                                {evt.status} {idx === events.length - 1 && isResearching ? <span className="pulse">●</span> : ''}
                            </div>
                            <div className="timeline-content">
                                {evt.message}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {finalReport && (
                <div className="glass-panel">
                    <div className="markdown-body">
                        <ReactMarkdown>{finalReport}</ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
      )}
    </>
  );
}

export default App;
