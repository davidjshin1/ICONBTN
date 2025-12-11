import { useState, useRef, useEffect } from 'react';
import imgUnGodlyLogo from '../assets/imgUnGodlyLogo.png';
import imgGroup41 from '../assets/imgGroup41.png';
import imgSend from '../assets/img.png';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generatedAssets, setGeneratedAssets] = useState([]);
  const [showGallery, setShowGallery] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    const userInput = input;
    const userMessage = { role: 'user', content: userInput };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    console.log('Sending request:', userInput);
    
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userInput })
      });
      
      console.log('Response status:', res.status);
      
      const data = await res.json();
      console.log('Response data:', data);
      
      if (!res.ok) {
        throw new Error(data.detail || `Server error: ${res.status}`);
      }
      
      const assistantMessage = {
        role: 'assistant',
        content: data.message,
        downloadUrl: data.download_url,
        assetType: data.asset_type,
        details: data.details,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
      if (data.download_url) {
        setGeneratedAssets(prev => [...prev, {
          url: data.download_url,
          type: data.asset_type,
          prompt: userInput,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (err) {
      console.error('Generation error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}. Please try again.`,
        isError: true
      }]);
    }
    setIsLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="bg-white overflow-hidden relative rounded-[32px] w-full max-w-[1327px] h-[900px] shadow-xl">
      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-2xl p-8 shadow-2xl flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-[#160211] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-[#160211] font-manrope font-medium">Generating your asset...</p>
            <p className="text-gray-400 text-sm">This may take 10-30 seconds</p>
          </div>
        </div>
      )}

      {/* Gallery Modal */}
      {showGallery && (
        <div className="absolute inset-0 bg-black/50 z-50 flex items-center justify-center p-8">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-manrope font-semibold">Generated Assets ({generatedAssets.length})</h2>
              <button onClick={() => setShowGallery(false)} className="text-gray-500 hover:text-gray-800 text-2xl">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {generatedAssets.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No assets generated yet</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {generatedAssets.map((asset, i) => (
                    <div key={i} className="border rounded-lg p-3 hover:shadow-md transition-shadow">
                      <div className="aspect-square bg-gray-100 rounded mb-2 flex items-center justify-center overflow-hidden">
                        <img src={asset.url} alt={asset.type} className="max-w-full max-h-full object-contain" />
                      </div>
                      <p className="text-xs text-gray-500 truncate">{asset.prompt}</p>
                      <a href={asset.url} download className="text-xs text-blue-600 hover:underline">Download</a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Background gradient blur */}
      <div className="absolute h-[464px] left-[calc(50%-10px)] top-[501px] -translate-x-1/2 w-[544px] pointer-events-none">
        <div className="absolute inset-[-96.98%_-68.01%_-107.76%_-91.91%]">
          <img 
            alt="" 
            className="block max-w-none w-full h-full opacity-50" 
            src={imgGroup41} 
          />
        </div>
      </div>
      
      {/* Gallery Button */}
      <button 
        onClick={() => setShowGallery(true)}
        className="absolute top-6 right-6 px-4 py-2 bg-[#160211] text-white rounded-lg text-sm hover:bg-[#2a0420] transition-colors flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        Gallery {generatedAssets.length > 0 && `(${generatedAssets.length})`}
      </button>

      {/* Logo and Title */}
      <div className="absolute flex flex-col gap-4 items-center left-1/2 top-16 -translate-x-1/2 w-[409px]">
        <div className="h-[50px] relative w-[267px]">
          <img 
            alt="UNGODLY Logo" 
            className="absolute inset-0 object-cover object-center w-full h-full" 
            src={imgUnGodlyLogo} 
          />
        </div>
        <p className="font-manrope font-normal text-[#160211] text-2xl text-center w-full">
          UI Asset Generator
        </p>
      </div>
      
      {/* Messages Area */}
      <div className="absolute top-40 left-1/2 -translate-x-1/2 w-[883px] h-[520px] overflow-y-auto px-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 text-center">
            <p className="text-lg mb-2">Welcome to the UNGODLY Asset Generator</p>
            <p className="text-sm">
              Try asking for: icons, CTA buttons, cards, boons, or gacha screens
            </p>
            <div className="mt-6 text-xs text-gray-300 max-w-md">
              <p className="mb-2">Examples:</p>
              <ul className="space-y-1">
                <li>"Give me a potion icon"</li>
                <li>"Create a primary CTA that says CONFIRM"</li>
                <li>"Make a fire damage decreased boon"</li>
                <li>"Generate a gacha with 2 primals"</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {messages.map((msg, i) => (
              <div 
                key={i} 
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`max-w-[70%] p-4 rounded-2xl ${
                    msg.role === 'user' 
                      ? 'bg-[#160211] text-white rounded-br-md' 
                      : msg.isError 
                        ? 'bg-red-50 text-red-700 rounded-bl-md border border-red-200'
                        : 'bg-gray-100 text-gray-800 rounded-bl-md'
                  }`}
                >
                  <p className="font-dm-sans text-sm">{msg.content}</p>
                  
                  {msg.downloadUrl && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <a 
                        href={msg.downloadUrl} 
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-[#160211] text-white rounded-lg text-sm hover:bg-[#2a0420] transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download {msg.assetType}
                      </a>
                    </div>
                  )}
                  
                  {msg.details && (
                    <div className="mt-2 text-xs text-gray-500">
                      {Object.entries(msg.details)
                        .filter(([_, v]) => v != null)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(' | ')}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-800 p-4 rounded-2xl rounded-bl-md">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                    <span className="ml-2 text-sm text-gray-500">Generating...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      {/* Input Field */}
      <div className="absolute bg-white border border-[rgba(22,2,17,0.3)] flex items-center gap-3 left-1/2 -translate-x-1/2 p-3 rounded-xl bottom-10 w-[883px] shadow-sm">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Create a UI asset..."
          disabled={isLoading}
          className="flex-1 outline-none font-dm-sans text-sm text-gray-800 placeholder:text-gray-400 disabled:opacity-50"
        />
        <button 
          onClick={sendMessage}
          disabled={isLoading || !input.trim()}
          className="w-9 h-9 flex items-center justify-center hover:opacity-80 transition-opacity disabled:opacity-40"
        >
          <img alt="Send" className="w-full h-full" src={imgSend} />
        </button>
      </div>
    </div>
  );
}
