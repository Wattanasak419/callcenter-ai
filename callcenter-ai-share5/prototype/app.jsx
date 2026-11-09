import React, { useState, useRef, useEffect } from 'react';

// ============================================================================
// 1. GLOBAL TEXT MODAL MODULE
// ============================================================================
const TranscriptModal = ({ transcript, onClose }) => {
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999
    }}>
      <div style={{
        backgroundColor: 'white', padding: '35px', borderRadius: '30px',
        width: '550px', maxWidth: '90%', position: 'relative', 
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '25px', right: '25px', background: 'none',
          border: 'none', fontSize: '24px', color: '#94a3b8', cursor: 'pointer'
        }}>&times;</button>
        <h3 style={{ color: '#1e3a8a', fontSize: '22px', fontWeight: '700', marginTop: 0, marginBottom: '20px' }}>
          Full Call Transcript
        </h3>
        <div style={{
          border: '1px solid #e2e8f0', borderRadius: '18px', padding: '20px',
          maxHeight: '320px', overflowY: 'auto', backgroundColor: '#f8fafc',
          lineHeight: '1.7', color: '#334155', fontSize: '15px'
        }}>{transcript}</div>
        <button onClick={onClose} style={{
          width: '100%', marginTop: '25px', padding: '14px', backgroundColor: '#3b82f6',
          color: 'white', border: 'none', borderRadius: '15px', fontWeight: '700', cursor: 'pointer'
        }}>Close Transcript</button>
      </div>
    </div>
  );
};

// ============================================================================
// 2. CALL RECORDS SUB-MODULES (Defined Outside to preserve input focus)
// ============================================================================
const DynamicCallRow = ({ file, selectedFiles, setSelectedTranscript, setIsTranscriptOpen, onDelete }) => {
  const [url] = useState(() => URL.createObjectURL(file));
  const dateObj = new Date(file.lastModified || Date.now());
  const displayDate = dateObj.toLocaleDateString();
  const displayTime = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const customerId = file.name.match(/actor\d+/i)?.[0] || "Unknown";

  const handleView = async () => {
    const audioBaseName = file.name.toLowerCase().replace(/\.[^/.]+$/, "");
    const transcriptFile = (selectedFiles || []).find(f => {
      const fName = f.name.toLowerCase();
      return (fName.endsWith('.txt') || fName.endsWith('.vtt') || fName.endsWith('.tsv')) && fName.includes(audioBaseName);
    });

    if (transcriptFile) {
      try {
        const text = await transcriptFile.text();
        const cleanText = text.replace(/WEBVTT|Kind:.*|Language:.*|(\d{2}:.* --> .*)/g, '').trim();
        setSelectedTranscript(cleanText || "Empty text format.");
      } catch (err) {
        setSelectedTranscript("Error: Failed to safely parse text stream data.");
      }
    } else {
      setSelectedTranscript(`Missing file: "${audioBaseName}.txt" not found in uploaded files.`);
    }
    setIsTranscriptOpen(true);
  };

  return (
    <tr style={{ fontSize: '14px', color: '#1e293b', borderBottom: '1px solid #f1f5f9' }}>
      <td style={{ textAlign: 'center', padding: '18px 0' }}>
        <div style={{ fontWeight: '600' }}>{displayDate}</div>
        <div style={{ fontSize: '12px', color: '#64748b' }}>{displayTime}</div>
      </td>
      <td style={{ textAlign: 'center', fontWeight: '600' }}>Max Verstappen</td>
      <td style={{ textAlign: 'center', color: '#64748b' }}>{customerId}</td>
      <td style={{ textAlign: 'center' }}>
        <span style={{ color: '#22c55e', backgroundColor: '#f0fdf4', padding: '5px 14px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>Positive</span>
      </td>
      <td style={{ textAlign: 'center' }}>
        <span style={{ backgroundColor: '#eff6ff', color: '#3b82f6', padding: '6px 14px', borderRadius: '8px', fontSize: '13px', fontWeight: '600' }}>General Inquiry</span>
      </td>
      <td style={{ textAlign: 'center' }}>
        <audio controls src={url} style={{ height: '40px', width: '230px', filter: 'grayscale(1) brightness(0.96)' }} />
      </td>
      <td style={{ textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <button onClick={handleView} style={{ padding: '8px 18px', borderRadius: '10px', border: 'none', backgroundColor: '#3b82f6', color: 'white', fontWeight: '700', cursor: 'pointer', fontSize: '12px' }}>View</button>
          <button onClick={onDelete} style={{ padding: '8px 18px', borderRadius: '10px', border: 'none', backgroundColor: '#ef4444', color: 'white', fontWeight: '700', cursor: 'pointer', fontSize: '12px' }}>Delete</button>
        </div>
      </td>
    </tr>
  );
};

const CallRecordsContent = ({ selectedFiles, setSelectedFiles, setSelectedTranscript, setIsTranscriptOpen, searchTerm, setSearchTerm, searchInputRef }) => {
  const audioFiles = selectedFiles.filter(f => f.type.includes('audio') || ['.flac', '.mp3', '.wav'].some(ext => f.name.toLowerCase().endsWith(ext)));
  const displayFiles = audioFiles.filter(file => searchTerm === "" || file.name.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', height: '100%' }}>
      <input ref={searchInputRef} type="text" placeholder="Search uploaded files..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ width: '100%', padding: '15px 25px', borderRadius: '50px', border: 'none', backgroundColor: '#f8fafc', fontSize: '14px', outline: 'none', color: '#1e293b', boxShadow: '0 2px 8px rgba(0,0,0,0.04)', marginBottom: '10px' }} />
      <div style={{ backgroundColor: 'white', borderRadius: '25px', padding: '0 40px 40px 40px', flex: 1, boxShadow: '0 4px 12px rgba(0,0,0,0.03)', overflowY: 'auto' }}>
        {displayFiles.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 20 }}>
              <tr style={{ textAlign: 'center' }}>
                {['Time Stamp', 'Agent Name', 'Customer ID', 'Sentiment', 'Topic', 'Recording', 'Actions'].map((h) => (
                  <th key={h} style={{ color: '#3b82f6', fontSize: '14px', fontWeight: '800', padding: '25px 10px 15px 10px', backgroundColor: 'white', borderBottom: '2px solid #f1f5f9' }}>{h.toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayFiles.map((file) => (
                <DynamicCallRow key={file.name} file={file} selectedFiles={selectedFiles} setSelectedTranscript={setSelectedTranscript} setIsTranscriptOpen={setIsTranscriptOpen} onDelete={() => setSelectedFiles(prev => prev.filter(f => f.name !== file.name))} />
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ display: 'flex', height: '100%', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', paddingTop: '60px' }}>
            <p style={{ fontSize: '16px', fontWeight: '500' }}>No call records found.</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// 3. UPLOAD AND ANALYZE SCREEN MODULE
// ============================================================================
const UploadContent = ({ selectedFiles, setSelectedFiles, fileInputRef, setIsDrawerOpen, setActiveAnalysis }) => {
  const triggerFileSelect = () => fileInputRef.current.click();

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const filtered = files.filter(f => !existingNames.has(f.name));
      return [...prev, ...filtered];
    });
    event.target.value = null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', height: '100%' }}>
      <input type="file" multiple accept="audio/*,.vtt,.tsv,.txt" ref={fileInputRef} onChange={handleFileUpload} style={{ display: 'none' }} />
      <div onClick={triggerFileSelect} style={{ flex: '0 0 200px', backgroundColor: '#f8fafc', border: '3px dashed #cbd5e1', borderRadius: '25px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
        <h2 style={{ color: '#3b82f6', fontSize: '20px', fontWeight: '700' }}>Drag or drop system metrics files here, or <span style={{ textDecoration: 'underline' }}>Browse</span></h2>
      </div>
      <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '25px', padding: '30px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
          <span style={{ fontWeight: '700', color: '#64748b', fontSize: '14px' }}>System Working Files</span>
          <span style={{ fontWeight: '700', color: '#64748b', fontSize: '14px' }}>Action Status</span>
        </div>
        <div>
          {selectedFiles.length > 0 ? (
            selectedFiles.map((file, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 5px', borderBottom: '1px solid #f8fafc' }}>
                <span style={{ color: '#1e293b', fontSize: '14px', fontWeight: '600' }}>{file.name}</span>
                {file.type.includes('audio') || ['.flac', '.mp3'].some(ext => file.name.toLowerCase().endsWith(ext)) ? (
                  <button onClick={() => { setActiveAnalysis(file); setIsDrawerOpen(true); }} style={{ padding: '8px 20px', borderRadius: '8px', backgroundColor: '#3b82f6', color: 'white', border: 'none', fontWeight: '700', cursor: 'pointer' }}>Analyze File</button>
                ) : (
                  <span style={{ fontSize: '12px', color: '#94a3b8', marginRight: '20px' }}>Text Index Linkage</span>
                )}
              </div>
            ))
          ) : (
            <div style={{ color: '#94a3b8', fontStyle: 'italic', textAlign: 'center', marginTop: '40px' }}>No system workspace paths initialized.</div>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 4. PLACEHOLDER CORE ANALYTIC VIEWS MODULES
// ============================================================================
const DashboardContent = () => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
    {[['Total Monitored Calls', '1,482', '+12.5%'], ['Overall System Sentiment', '84.2%', '+3.1%'], ['Avg Response Efficiency', '2m 14s', '-18s']].map(([title, val, trend]) => (
      <div key={title} style={{ backgroundColor: 'white', padding: '25px', borderRadius: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
        <h4 style={{ color: '#64748b', margin: '0 0 10px 0', fontSize: '14px' }}>{title}</h4>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
          <span style={{ fontSize: '28px', fontWeight: '700', color: '#1e293b' }}>{val}</span>
          <span style={{ fontSize: '12px', color: trend.startsWith('+') ? '#22c55e' : '#ef4444', fontWeight: '600' }}>{trend}</span>
        </div>
      </div>
    ))}
  </div>
);

const InsightsContent = () => <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '25px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}><h3>Automated Extraction Metrics</h3><p style={{ color: '#64748b' }}>Data categorization arrays generated automatically using processing loops via faster-whisper turbo configurations.</p></div>;
const AgentPerformanceContent = () => <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '25px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}><h3>Performance Metrics Matrix</h3><p style={{ color: '#64748b' }}>Cross-referencing customer experience records matching system parameters.</p></div>;
const ReportsContent = () => <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '25px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}><h3>Export Status Window</h3><p style={{ color: '#64748b' }}>System exports ready across standard schemas.</p></div>;
const SettingsContent = () => <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '25px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}><h3>Configuration Framework</h3><p style={{ color: '#64748b' }}>System hooks matching environment properties directly.</p></div>;

// ============================================================================
// 5. RIGHT SIDEBAR COMPILATION ANALYSIS DRAWER MODULE
// ============================================================================
const AnalysisDrawer = ({ isOpen, onClose, activeFile }) => {
  if (!isOpen || !activeFile) return null;
  return (
    <div style={{ position: 'fixed', top: 0, right: 0, width: '450px', height: '100vh', backgroundColor: 'white', boxShadow: '-10px 0 30px rgba(0,0,0,0.05)', zIndex: 5000, padding: '40px', display: 'flex', flexDirection: 'column', gap: '25px', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, color: '#1e293b', fontSize: '20px' }}>Real-time Call Analysis</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#94a3b8' }}>&times;</button>
      </div>
      <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '15px' }}>
        <div style={{ fontSize: '12px', color: '#64748b' }}>TARGET RECORD</div>
        <div style={{ fontWeight: '600', color: '#1e293b', fontSize: '14px', overflowX: 'hidden' }}>{activeFile.name}</div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <label style={{ fontSize: '12px', fontWeight: '700', color: '#64748b' }}>EXTRACTED SENTIMENT</label>
          <div style={{ display: 'inline-block', width: '100%', padding: '12px', backgroundColor: '#f0fdf4', color: '#22c55e', fontWeight: '700', borderRadius: '10px', marginTop: '5px', boxSizing: 'border-box', textAlign: 'center' }}>POSITIVE REAL-TIME</div>
        </div>
        <div>
          <label style={{ fontSize: '12px', fontWeight: '700', color: '#64748b' }}>TOPICAL CLASSIFICATION</label>
          <div style={{ padding: '12px', backgroundColor: '#eff6ff', color: '#3b82f6', fontWeight: '700', borderRadius: '10px', marginTop: '5px', textAlign: 'center' }}>GENERAL ROUTING INDEX</div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 6. MAIN GLOBAL APPLICATION SHELL PANEL ENGINE (App)
// ============================================================================
const App = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedTranscript, setSelectedTranscript] = useState('');
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Slide Drawer states
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeAnalysis, setActiveAnalysis] = useState(null);

  // Core stable references tracking navigation and memory pipelines
  const fileInputRef = useRef(null);
  const searchInputRef = useRef(null);

  const menuItems = [
    { id: 'Dashboard', label: 'Dashboard' },
    { id: 'Upload and Analyze', label: 'Upload and Analyze' },
    { id: 'Call Records', label: 'Call Records' },
    { id: 'Insights', label: 'Insights' },
    { id: 'Agent Performance', label: 'Agent Performance' },
    { id: 'Reports', label: 'Reports' },
    { id: 'Settings', label: 'Settings' }
  ];

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', backgroundColor: '#f1f5f9', fontFamily: 'system-ui, -apple-system, sans-serif', overflow: 'hidden' }}>
      
      {/* LEFT HAND GLOBAL NAVIGATION SIDEBAR */}
      <div style={{ width: '280px', backgroundColor: '#93c5fd', display: 'flex', flexDirection: 'column', padding: '30px 20px', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '40px', paddingLeft: '10px' }}>
          <div style={{ width: '12px', height: '24px', backgroundColor: '#1e3a8a', borderRadius: '4px' }}></div>
          <span style={{ fontSize: '22px', fontWeight: '900', color: 'white', letterSpacing: '0.5px' }}>OMAZZ CALLING</span>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
          {menuItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button key={item.id} onClick={() => setActiveTab(item.id)} style={{ display: 'flex', alignItems: 'center', padding: '14px 20px', borderRadius: '15px', border: 'none', backgroundColor: isActive ? 'rgba(255, 255, 255, 0.6)' : 'transparent', color: isActive ? '#1e3a8a' : 'white', fontWeight: '700', fontSize: '14px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s ease' }}>
                {item.label}
              </button>
            );
          })}
        </div>
        
        <button style={{ display: 'flex', alignItems: 'center', padding: '14px 20px', borderRadius: '15px', border: 'none', backgroundColor: 'transparent', color: 'white', fontWeight: '700', fontSize: '14px', cursor: 'pointer', textAlign: 'left' }}>Logout</button>
      </div>

      {/* CENTER WORKSPACE LAYOUT WRAPPER PANELS FRAME */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Header Ribbon Row navbar */}
        <div style={{ height: '80px', padding: '0 40px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxSizing: 'border-box' }}>
          <span style={{ color: '#64748b', fontSize: '14px', fontWeight: '600' }}>{activeTab}</span>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button style={{ padding: '10px 20px', borderRadius: '12px', border: 'none', backgroundColor: '#3b82f6', color: 'white', fontSize: '13px', fontWeight: '700', cursor: 'pointer' }}>Last 30 Days</button>
            <button style={{ padding: '10px 20px', borderRadius: '12px', border: 'none', backgroundColor: '#1e3a8a', color: 'white', fontSize: '13px', fontWeight: '700', cursor: 'pointer' }}>Export Report</button>
          </div>
        </div>

        {/* Dynamic Inner Tab View Content View Router Switch */}
        <div style={{ flex: 1, padding: '0 40px 40px 40px', overflowY: 'auto', boxSizing: 'border-box' }}>
          {activeTab === 'Dashboard' && <DashboardContent />}
          {activeTab === 'Upload and Analyze' && (
            <UploadContent selectedFiles={selectedFiles} setSelectedFiles={setSelectedFiles} fileInputRef={fileInputRef} setIsDrawerOpen={setIsDrawerOpen} setActiveAnalysis={setActiveAnalysis} />
          )}
          {activeTab === 'Call Records' && (
            <CallRecordsContent selectedFiles={selectedFiles} setSelectedFiles={setSelectedFiles} setSelectedTranscript={setSelectedTranscript} setIsTranscriptOpen={setIsTranscriptOpen} searchTerm={searchTerm} setSearchTerm={setSearchTerm} searchInputRef={searchInputRef} />
          )}
          {activeTab === 'Insights' && <InsightsContent />}
          {activeTab === 'Agent Performance' && <AgentPerformanceContent />}
          {activeTab === 'Reports' && <ReportsContent />}
          {activeTab === 'Settings' && <SettingsContent />}
        </div>
      </div>

      {/* SLIDE OUT METRIC CONTEXT ANALYSIS WRAPPER DRAWER */}
      <AnalysisDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} activeFile={activeAnalysis} />

      {/* PORTAL OVERLAY INJECTION TRIGERED INTERNALLY */}
      {isTranscriptOpen && (
        <TranscriptModal transcript={selectedTranscript} onClose={() => setIsTranscriptOpen(false)} />
      )}

    </div>
  );
};

export default App;