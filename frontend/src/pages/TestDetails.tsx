import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { TestRun, WSMessage, TestRunDetail } from '@/types';
import { TkCard, TkButton } from '@takeoff-ui/react';
import { format } from 'date-fns';

// Helper to map historical results to WSMessage format for consistent rendering
const mapResultToMessage = (result: any): WSMessage => {
    let data: any = { ...result.data };

    if (result.step_type === 'tool_call') {
        data = {
            tool_name: result.tool_name,
            arguments: result.data
        };
    } else if (result.step_type === 'tool_result') {
        data = {
            tool_name: result.tool_name,
            result: {
                success: result.success,
                data: result.data,
                error: result.error_message
            }
        };
    } else if (result.step_type === 'llm_response') {
        data = { content: result.content };
    } else if (result.step_type === 'error') {
        data = { error: result.error_message || result.content };
    }

    return {
        type: result.step_type,
        test_run_id: result.test_run_id,
        sequence: result.sequence,
        data,
        timestamp: result.created_at
    };
};

export function TestDetails() {
    const { id } = useParams<{ id: string }>();
    const [testRun, setTestRun] = useState<TestRun | null>(null);
    const [messages, setMessages] = useState<WSMessage[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentScreenshot, setCurrentScreenshot] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'logs' | 'preview'>('preview');

    const wsRef = useRef<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (id) {
            loadTestRun(parseInt(id));
        }
        return () => {
            wsRef.current?.close();
        };
    }, [id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const loadTestRun = async (testId: number) => {
        setIsLoading(true);
        try {
            const data = await apiClient.getTestRun(testId) as TestRunDetail;
            setTestRun(data);

            // If completed, map results to messages
            if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                if (data.results) {
                    const historicalMessages = data.results.map(mapResultToMessage);
                    setMessages(historicalMessages);
                }
            }
            // If running/pending, connect to WebSocket
            else if (['running', 'pending'].includes(data.status)) {
                // First load any existing results
                if (data.results) {
                    setMessages(data.results.map(mapResultToMessage));
                }
                connectWebSocket(testId);
            }
        } catch (err) {
            console.error('Failed to load test run:', err);
            setError('Failed to load test details');
        } finally {
            setIsLoading(false);
        }
    };

    const connectWebSocket = (testId: number) => {
        const token = apiClient.getAccessToken();
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/tests/${testId}/execute?token=${token}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (event) => {
            const message: WSMessage = JSON.parse(event.data);

            if (message.type === 'ping') return;

            // Handle viewport update
            if (message.type === 'viewport_update') {
                const imageUrl = message.data.image as string;
                setCurrentScreenshot(imageUrl);
                return; // Don't add to logs
            }

            setMessages(prev => {
                // Avoid duplicates if utilizing sequence number
                if (prev.some(m => m.sequence === message.sequence && m.type === message.type)) {
                    return prev;
                }
                return [...prev, message];
            });

            if (message.type === 'complete' || message.type === 'error' || message.type === 'cancelled') {
                // Refresh full details to get final state
                loadTestRun(testId);
            }
        };

        ws.onerror = () => {
            console.error('WebSocket error');
        };
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-700 border-green-200';
            case 'failed': return 'bg-red-100 text-red-700 border-red-200';
            case 'running': return 'bg-blue-100 text-blue-700 border-blue-200';
            case 'pending': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            default: return 'bg-slate-100 text-slate-700 border-slate-200';
        }
    };

    const getMessageIcon = (type: string) => {
        switch (type) {
            case 'status':
                return (
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                );
            case 'tool_call':
                return (
                    <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        </svg>
                    </div>
                );
            case 'tool_result':
                return (
                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                );
            case 'llm_response':
                return (
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                    </div>
                );
            case 'complete':
                return (
                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                );
            case 'error':
                return (
                    <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                );
            default:
                return null;
        }
    };

    const renderMessageContent = (msg: WSMessage) => {
        const data = msg.data;

        switch (msg.type) {
            case 'status':
                return <p className="text-slate-600">{data.message as string}</p>;

            case 'tool_call':
                return (
                    <div>
                        <p className="text-purple-600 font-medium">{data.tool_name as string}</p>
                        <pre className="mt-2 p-2 bg-slate-100 rounded text-xs text-slate-600 overflow-x-auto">
                            {JSON.stringify(data.arguments, null, 2)}
                        </pre>
                    </div>
                );

            case 'tool_result':
                const result = data.result as { success: boolean; data?: unknown; error?: string };
                const resultDataStr = result?.data !== undefined
                    ? (typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2))
                    : null;
                return (
                    <div>
                        <p className={`font-medium ${result?.success ? 'text-green-600' : 'text-red-600'}`}>
                            {data.tool_name as string}: {result?.success ? 'Success' : 'Failed'}
                        </p>
                        {resultDataStr && (
                            <pre className="mt-2 p-2 bg-slate-100 rounded text-xs text-slate-600 overflow-x-auto max-h-40">
                                {resultDataStr}
                            </pre>
                        )}
                        {result?.error && (
                            <p className="mt-2 text-sm text-red-600">{result.error}</p>
                        )}
                    </div>
                );

            case 'llm_response':
                return <p className="text-slate-600 whitespace-pre-wrap">{data.content as string}</p>;

            case 'complete':
                return <p className="text-green-600 font-medium">{data.message as string}</p>;

            case 'error':
                return <p className="text-red-600">{data.error as string}</p>;

            default:
                return <pre className="text-xs text-slate-500">{JSON.stringify(data, null, 2)}</pre>;
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (error || !testRun) {
        return (
            <div className="text-center py-12">
                <div className="text-red-500 mb-4">
                    <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <h2 className="text-xl font-bold text-slate-800 mb-2">Error Loading Test</h2>
                <p className="text-slate-500 mb-6">{error || 'Test not found'}</p>
                <Link to="/tests">
                    <TkButton variant="secondary" label="Back to History" />
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <h1 className="text-2xl font-bold text-slate-800">Test Details</h1>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getStatusBadgeClass(testRun.status)}`}>
                            {testRun.status}
                        </span>
                    </div>
                    <p className="text-slate-500 font-mono text-sm">#{testRun.id}</p>
                </div>
                <div className="flex items-center gap-4">
                    {/* View Toggle */}
                    <div className="flex bg-slate-100 p-1 rounded-lg">
                        <button
                            onClick={() => setActiveTab('preview')}
                            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === 'preview'
                                ? 'bg-white text-blue-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            Live View
                        </button>
                        <button
                            onClick={() => setActiveTab('logs')}
                            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === 'logs'
                                ? 'bg-white text-blue-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            Logs
                        </button>
                    </div>
                    <Link to="/tests">
                        <TkButton variant="secondary" label="Back to History" />
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Info Card - Always visible */}
                <div className="lg:col-span-1 space-y-6">
                    <TkCard>
                        <div className="p-6 bg-white rounded-lg border border-slate-200 space-y-4">
                            <div>
                                <h3 className="text-sm font-medium text-slate-500 mb-1">Project</h3>
                                <p className="text-slate-800 font-medium">{testRun.project_name || `Project #${testRun.project_id}`}</p>
                            </div>

                            <div>
                                <h3 className="text-sm font-medium text-slate-500 mb-1">Command</h3>
                                <p className="text-slate-800 text-sm whitespace-pre-wrap">{testRun.command}</p>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h3 className="text-sm font-medium text-slate-500 mb-1">Started</h3>
                                    <p className="text-slate-800 text-sm">
                                        {testRun.started_at ? format(new Date(testRun.started_at), 'MMM d, HH:mm:ss') : '-'}
                                    </p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-medium text-slate-500 mb-1">Duration</h3>
                                    <p className="text-slate-800 text-sm">
                                        {testRun.duration_ms ? `${(testRun.duration_ms / 1000).toFixed(1)}s` : '-'}
                                    </p>
                                </div>
                            </div>

                            <div>
                                <h3 className="text-sm font-medium text-slate-500 mb-1">Triggered By</h3>
                                <p className="text-slate-800 text-sm">{testRun.trigger_type}</p>
                            </div>
                        </div>
                    </TkCard>

                    {/* Live Preview (Small) - Only visible when in Logs mode and we have a screenshot */}
                    {activeTab === 'logs' && currentScreenshot && (
                        <div className="rounded-lg overflow-hidden border border-slate-200 shadow-sm">
                            <img src={currentScreenshot} alt="Live Preview" className="w-full h-auto" />
                            <div className="bg-slate-50 p-2 text-center text-xs text-slate-500 border-t border-slate-200">
                                Live Preview
                            </div>
                        </div>
                    )}
                </div>

                {/* Main Content Area */}
                <div className="lg:col-span-2">
                    {activeTab === 'preview' ? (
                        <TkCard>
                            <div className="p-6 bg-white rounded-lg border border-slate-200 h-[600px] flex flex-col">
                                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                                    <span className="relative flex h-3 w-3">
                                        {['running', 'pending'].includes(testRun.status) && (
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                        )}
                                        <span className={`relative inline-flex rounded-full h-3 w-3 ${['running', 'pending'].includes(testRun.status) ? 'bg-red-500' : 'bg-slate-400'}`}></span>
                                    </span>
                                    Browser Viewport
                                </h3>

                                <div className="flex-1 bg-slate-100 rounded-lg flex items-center justify-center overflow-hidden border border-slate-200 relative">
                                    {currentScreenshot ? (
                                        <img
                                            src={currentScreenshot}
                                            alt="Browser Viewport"
                                            className="max-w-full max-h-full object-contain shadow-lg"
                                        />
                                    ) : (
                                        <div className="text-center text-slate-400">
                                            <svg className="w-16 h-16 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                            </svg>
                                            <p>Waiting for live stream...</p>
                                            {testRun.status === 'completed' && <p className="text-sm mt-1">Test completed</p>}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </TkCard>
                    ) : (
                        <TkCard>
                            <div className="p-6 bg-white rounded-lg border border-slate-200 h-[600px] flex flex-col">
                                <h3 className="text-lg font-semibold text-slate-800 mb-4">Execution Log</h3>
                                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                                    {messages.length > 0 ? (
                                        messages.map((msg, index) => (
                                            <div
                                                key={index}
                                                className="flex gap-3 p-3 bg-slate-50 rounded-lg animate-slide-up transition-all"
                                            >
                                                {getMessageIcon(msg.type)}
                                                <div className="flex-1 min-w-0">
                                                    {renderMessageContent(msg)}
                                                    {msg.timestamp && (
                                                        <p className="text-xs text-slate-400 mt-1">
                                                            {format(new Date(msg.timestamp), 'HH:mm:ss')}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="h-full flex items-center justify-center text-slate-500">
                                            <p>No execution logs available</p>
                                        </div>
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>
                            </div>
                        </TkCard>
                    )}
                </div>
            </div>
        </div>
    );
}
