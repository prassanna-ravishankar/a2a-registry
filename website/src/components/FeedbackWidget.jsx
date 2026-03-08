import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';
import useMediaQuery from '@/hooks/useMediaQuery';

const SESSION_KEY = 'feedback_submitted';

const FeedbackWidget = () => {
    const [open, setOpen] = useState(false);
    const [message, setMessage] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [hidden, setHidden] = useState(() => sessionStorage.getItem(SESSION_KEY) === '1');
    const isMobile = useMediaQuery('(max-width: 767px)');
    const textareaRef = useRef(null);

    useEffect(() => {
        if (open && textareaRef.current) {
            textareaRef.current.focus();
        }
    }, [open]);

    if (hidden) return null;

    const handleSubmit = () => {
        if (!message.trim()) return;
        window.posthog?.capture('user_feedback', { message: message.trim() });
        setSubmitted(true);
        sessionStorage.setItem(SESSION_KEY, '1');
        setTimeout(() => setHidden(true), 1500);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
        if (e.key === 'Escape') setOpen(false);
    };

    return (
        <div className={`fixed z-50 flex flex-col gap-2 ${isMobile ? 'bottom-3 right-3 left-3 items-end' : 'bottom-4 right-4 items-end'}`}>
            {open && (
                <div className={`flex flex-col border border-zinc-700 bg-zinc-900 shadow-2xl ${isMobile ? 'w-[min(100%,22rem)]' : 'w-72'}`}>
                    <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
                        <span className="text-[10px] font-mono text-emerald-500 tracking-wider">SEND_FEEDBACK</span>
                        <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-zinc-200 transition-colors">
                            <X className="w-3.5 h-3.5" />
                        </button>
                    </div>

                    {submitted ? (
                        <div className="px-3 py-4 text-xs font-mono text-emerald-400 text-center">
                            FEEDBACK_RECEIVED // THANK_YOU
                        </div>
                    ) : (
                        <>
                            <textarea
                                ref={textareaRef}
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="What's on your mind?"
                                rows={4}
                                className="bg-transparent text-zinc-200 text-xs font-mono placeholder:text-zinc-600 resize-none p-3 outline-none border-b border-zinc-800"
                            />
                            <div className="flex items-center justify-between px-3 py-2">
                                <span className="text-[10px] font-mono text-zinc-600">⌘+Enter to send</span>
                                <button
                                    onClick={handleSubmit}
                                    disabled={!message.trim()}
                                    className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-[10px] font-mono uppercase tracking-wider"
                                >
                                    <Send className="w-3 h-3" />
                                    SUBMIT
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}

            <button
                onClick={() => setOpen((o) => !o)}
                className={`flex items-center gap-2 border border-zinc-700 bg-zinc-900 text-[10px] font-mono uppercase tracking-wider text-zinc-400 shadow-lg transition-all hover:border-emerald-500/50 hover:text-emerald-400 ${isMobile ? 'px-3 py-2.5' : 'px-3 py-2'}`}
            >
                <MessageSquare className="w-3.5 h-3.5" />
                FEEDBACK
            </button>
        </div>
    );
};

export default FeedbackWidget;
