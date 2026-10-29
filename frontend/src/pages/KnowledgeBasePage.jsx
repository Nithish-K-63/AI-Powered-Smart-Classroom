import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Upload,
  FileText,
  CheckCircle2,
  Database,
  Layers,
  Sparkles,
  RefreshCw,
  FolderPlus,
} from 'lucide-react';
import api from '../services/api';

export default function KnowledgeBasePage() {
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'upload'
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  // Upload Form state
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('projector');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [docs, h] = await Promise.all([
        api.getKnowledgeDocuments(),
        api.getHealth(),
      ]);
      setDocuments(docs);
      setHealth(h);
    } catch (err) {
      console.error('Failed to load knowledge base:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpload = async e => {
    e.preventDefault();
    if (!selectedFile || !title.trim() || uploading) return;

    setUploading(true);
    setUploadSuccess(null);
    try {
      const res = await api.uploadKnowledgeManual(
        selectedFile,
        title,
        category,
        'campus_admin'
      );
      setUploadSuccess(`Manual indexed! Created ${res.chunks_indexed} grounded chunks into ChromaDB vector store.`);
      setTitle('');
      setSelectedFile(null);
      loadData();
      setActiveTab('documents');
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* ChromaDB Telemetry Card matching Figma */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
              ChromaDB Semantic Vector Index
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-2">
            Campus AV Technical Knowledge Base
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            SOP manuals and manufacturer troubleshooting guides indexed with dense embeddings for Qwen3-8B context grounding.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center min-w-[110px]">
            <span className="text-[10px] font-bold text-slate-400 uppercase block">Active Chunks</span>
            <span className="text-xl font-extrabold text-indigo-600">
              {health?.vector_store_chunks || 20}
            </span>
          </div>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center min-w-[110px]">
            <span className="text-[10px] font-bold text-slate-400 uppercase block">Retriever</span>
            <span className="text-xs font-bold text-emerald-600">Grounded</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('documents')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'documents'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Indexed Manuals ({documents.length})
        </button>

        <button
          onClick={() => setActiveTab('upload')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
            activeTab === 'upload'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Ingest New Manual</span>
        </button>
      </div>

      {/* Upload Success Banner */}
      {uploadSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{uploadSuccess}</span>
        </div>
      )}

      {/* Tab: Indexed Documents */}
      {activeTab === 'documents' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">Approved Campus SOP Documents</h3>
            <button
              onClick={loadData}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {documents.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No manuals registered yet. Use the Ingest tab to upload documents.
              </div>
            ) : (
              documents.map(doc => (
                <div key={doc.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-xs">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{doc.title}</h4>
                      <p className="text-[11px] text-slate-500">
                        {doc.filename} • Format: <span className="uppercase font-semibold">{doc.file_type}</span> • Category: <span className="capitalize font-semibold">{doc.metadata?.equipment_category || 'AV'}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-right">
                    <div className="text-xs">
                      <span className="font-bold text-indigo-600 block">{doc.total_chunks} Chunks</span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(doc.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab: Upload Manual */}
      {activeTab === 'upload' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 max-w-xl mx-auto">
          <h3 className="text-base font-bold text-slate-900 mb-1">
            Manual Ingestion & Semantic Chunking
          </h3>
          <p className="text-xs text-slate-500 mb-5">
            Uploaded manuals are automatically partitioned into 400-token chunks with 60-token sliding overlap and embedded into ChromaDB.
          </p>

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Document Title</label>
              <input
                type="text"
                placeholder="e.g. Epson PowerLite 2250U Field Operating Manual"
                value={title}
                onChange={e => setTitle(e.target.value)}
                required
                className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Hardware Category</label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 capitalize"
              >
                <option value="projector">Projector</option>
                <option value="smart_board">Smart Board</option>
                <option value="microphone">Microphone</option>
                <option value="speaker">Speaker System</option>
                <option value="display">Digital Display</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Select File (PDF, TXT, MD)</label>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={e => setSelectedFile(e.target.files[0])}
                required
                className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
            </div>

            <button
              type="submit"
              disabled={uploading || !selectedFile || !title.trim()}
              className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/20 transition-colors"
            >
              <span>{uploading ? 'Processing & Chunking...' : 'Upload & Ingest to ChromaDB'}</span>
              <Upload className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
