import React, { useState, useEffect } from 'react';
import { Modal, Button, Row, Col, Badge, Alert } from 'react-bootstrap';
import { toast } from 'react-toastify';
import ApiService from '../services/ApiService';
import ChatModal from './ChatModal';

const RecordModal = ({ record, show, onHide, onAnalyze, onAskQuestion, getSeverityClass, getSeverityText, isAnalyzing, analysisProgress, analysisStatus }) => {
  const [similarRecords, setSimilarRecords] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [showAllSimilar, setShowAllSimilar] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [savingTag, setSavingTag] = useState(false);
  const [tags, setTags] = useState([]);
  const [visibility, setVisibility] = useState('self');
  const [savingVisibility, setSavingVisibility] = useState(false);
  const [contextText, setContextText] = useState('');
  const [savingContext, setSavingContext] = useState(false);
  const [devFeedbackText, setDevFeedbackText] = useState('');
  const [savingDevFeedback, setSavingDevFeedback] = useState(false);
  const [devFeedbackThresholdInput, setDevFeedbackThresholdInput] = useState('');
  const [similarityMin, setSimilarityMin] = useState(0.8);
  const [similarityMinInput, setSimilarityMinInput] = useState('80');
  const [refreshingSimilar, setRefreshingSimilar] = useState(false);
  const [showDevSources, setShowDevSources] = useState(false);

  useEffect(() => {
    if (show && record) {
      loadSimilarRecords();
    }
  }, [show, record]);

  // Sync local tags state when record changes
  useEffect(() => {
    setTags(Array.isArray(record?.tags) ? record.tags : []);
  }, [record]);

  // Initialize local visibility when record changes
  useEffect(() => {
    if (record && typeof record.visibility === 'string') {
      setVisibility(record.visibility || 'self');
    }
  }, [record]);

  // Initialize editable context when record changes
  useEffect(() => {
    setContextText(typeof record?.context === 'string' ? record.context : '');
    setDevFeedbackText(typeof record?.dev_feedback === 'string' ? record.dev_feedback : '');
  }, [record]);

  const loadSimilarRecords = async () => {
    if (!record) return;

    try {
      setLoadingSimilar(true);
      const response = await ApiService.getSimilarRecords(record.record_id, { min: similarityMin, limit: 200 });
      let similar = (response.similar_records || [])
        .filter(r => {
          const s = r.similarity_score;
          return (s > 1 ? s : s * 100) >= (similarityMin * 100);
        })
        .sort((a, b) => {
          const scoreA = a.similarity_score > 1 ? a.similarity_score : a.similarity_score * 100;
          const scoreB = b.similarity_score > 1 ? b.similarity_score : b.similarity_score * 100;
          return scoreB - scoreA;
        });

      // Add top match if it exists and is different from the first similar record
      if (record.similar_to && record.similarity_pct) {
        const topMatch = {
          record_id: record.similar_to,
          similarity_score: record.similarity_pct / 100,
          isTopMatch: true
        };
        
        // Check if top match is already in similar records
        const existsInSimilar = similar.some(r => r.record_id === record.similar_to);
        if (!existsInSimilar) {
          similar.unshift(topMatch);
        }
      }
      
      setSimilarRecords(similar);
    } catch (error) {
      console.error('Failed to load similar records:', error);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const handleDownload = async (filePath) => {
    try {
      await ApiService.downloadFile(filePath);
      toast.success('File download started');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Download failed: ' + error.message);
    }
  };

  const handleSaveVisibility = async () => {
    if (!record || !visibility) return;
    try {
      setSavingVisibility(true);
      await ApiService.updateRecordVisibility(record.record_id, visibility);
      toast.success('Visibility updated');
    } catch (error) {
      toast.error('Failed to update visibility: ' + error.message);
    } finally {
      setSavingVisibility(false);
    }
  };

  if (!record) return null;

  const analyzed = !!(record.genapi && record.genapi.analyzed);
  const problemsCount = analyzed && record.genapi && Array.isArray(record.genapi.problems)
    ? record.genapi.problems.length : '-';

  return (
    <>
    <Modal 
      show={show} 
      onHide={onHide} 
      size="xl" 
      centered
      className="record-modal"
      style={{ 
        maxWidth: '100vw', 
        width: '100vw',
        height: '100vh',
        margin: 0
      }}
    >
      <Modal.Header>
        <Modal.Title>
          <i className="fas fa-file-alt me-2"></i>
          {record.title ? record.title : `${record.record_id}`}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body style={{ height: 'calc(100vh - 120px)', overflowY: 'auto', padding: '2rem' }}>
        {/* Header Information */}
        <Row className="mb-4">
          <Col md={6}>
            <div className="card h-100">
              <div className="card-body">
                <h5 className="card-title mb-3">
                  <i className="fas fa-info-circle me-2 text-primary"></i>
                  Basic Information
                </h5>
                <div className="mb-3">
                  <strong>Title:</strong> 
                  <span className="ms-2">{record.title || 'Untitled'}</span>
                </div>
                <div className="mb-3">
                  <strong>Severity:</strong> 
                  <Badge className={`ms-2 severity-${getSeverityClass(record.overall_severity)}`}>
                    {getSeverityText(record.overall_severity)}
                  </Badge>
                </div>
                <div className="mb-3">
                  <strong>Created:</strong> 
                  <span className="ms-2">{(() => {
                    const ts = record.created_at;
                    const hasZone = /Z|[+-]\d{2}:\d{2}$/.test(ts || '');
                    const d = new Date(hasZone ? ts : (ts ? ts + 'Z' : ''));
                    return isNaN(d.getTime()) ? '-' : d.toLocaleString();
                  })()}</span>
                </div>
                <div className="mb-3">
                  <strong>Visibility:</strong> 
                  <div className="d-flex align-items-center ms-2 mt-1">
                    <select
                      className="form-select form-select-sm"
                      style={{ maxWidth: 220 }}
                      value={visibility}
                      onChange={(e) => setVisibility(e.target.value)}
                      disabled={savingVisibility}
                    >
                      <option value="self">Private (Only Me)</option>
                      <option value="team">Team</option>
                      <option value="public">Public</option>
                    </select>
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      className="ms-2"
                      disabled={savingVisibility || visibility === (record.visibility || 'self')}
                      onClick={handleSaveVisibility}
                    >
                      {savingVisibility ? (
                        <>
                          <i className="fas fa-spinner fa-spin me-1"></i>
                          Saving...
                        </>
                      ) : (
                        <>Save</>
                      )}
                    </Button>
                  </div>
                </div>
                
                <div className="mt-3">
                  <strong>Context:</strong>
                  <div className="ms-2 mt-1">
                    <textarea
                      className="form-control"
                      rows="6"
                      placeholder="Add helpful context about this log... (use Save to persist)"
                      style={{ minHeight: 150, maxHeight: 260, overflowY: 'auto' }}
                      value={contextText}
                      onChange={(e) => setContextText(e.target.value)}
                    />
                    <div className="mt-2 d-flex justify-content-end gap-2">
                      <Button
                        variant="outline-secondary"
                        size="sm"
                        disabled={savingContext || (record?.context === contextText)}
                        onClick={async () => {
                          try {
                            setSavingContext(true);
                            await ApiService.updateRecordContext(record.record_id, contextText);
                            if (record) {
                              record.context = contextText;
                            }
                            toast.success('Context saved');
                          } catch (err) {
                            toast.error('Failed to save context');
                          } finally {
                            setSavingContext(false);
                          }
                        }}
                      >
                        {savingContext ? (
                          <>
                            <i className="fas fa-spinner fa-spin me-1"></i>
                            Saving
                          </>
                        ) : (
                          <>Save</>
                        )}
                      </Button>
                      <Button
                        variant="outline-danger"
                        size="sm"
                        disabled={savingContext || !contextText}
                        onClick={() => setContextText('')}
                      >
                        Clear
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Col>
          <Col md={6}>
            <div className="card mb-3">
              <div className="card-body">
                <h5 className="card-title mb-3">
                  <i className="fas fa-chart-bar me-2 text-primary"></i>
                  Statistics
                </h5>
                <div className="mb-2">
                  <strong>Raw Lines:</strong> 
                  <span className="ms-2">{record.raw_stats?.line_count || 0}</span>
                </div>
                <div className="mb-2">
                  <strong>Processed Lines:</strong> 
                  <span className="ms-2">{record.processed_stats?.line_count || 0}</span>
                </div>
                <div className="mb-2">
                  <strong>File Size:</strong> 
                  <span className="ms-2">{((record.raw_stats?.size_bytes || 0) / 1024).toFixed(2)} KB</span>
                </div>
                <div className="mb-0">
                  <strong>Problems Found:</strong> 
                  <span className="ms-2">{problemsCount}</span>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-body">
                <h5 className="card-title mb-3">
                  <i className="fas fa-tags me-2 text-primary"></i>
                  Tags
                </h5>
                <div className="mb-3">
                  <strong>Add Tag:</strong>
                  <div className="input-group input-group-sm mt-1" style={{ maxWidth: '100%' }}>
                    <input
                      className="form-control"
                      type="text"
                      placeholder="Enter tag and press Save"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      disabled={savingTag}
                    />
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      disabled={savingTag || !newTag.trim()}
                      onClick={async () => {
                        try {
                          setSavingTag(true);
                          await ApiService.api.patch(`/records/${record.record_id}/tags`, { tags: [newTag.trim()] });
                          toast.success('Tag added');
                          setNewTag('');
                          setTags((prev) => Array.from(new Set([...(prev || []), newTag.trim()])));
                        } catch (err) {
                          toast.error('Failed to add tag: ' + (err?.message || ''));
                        } finally {
                          setSavingTag(false);
                        }
                      }}
                    >
                      {savingTag ? (
                        <>
                          <i className="fas fa-spinner fa-spin me-1"></i>
                          Saving
                        </>
                      ) : (
                        <>Save</>
                      )}
                    </Button>
                  </div>
                </div>
                <div>
                  <strong>Tags</strong>
                  {(tags || []).length > 0 ? (
                    <div className="d-flex flex-wrap mt-2" style={{ gap: '0.5rem', maxHeight: 160, overflowY: 'auto', paddingRight: '0.25rem' }}>
                      {(tags || []).map(tag => (
                        <Badge key={tag} bg="secondary" className="me-2 mb-2 px-3 py-2">
                          <span className="me-2">{tag}</span>
                          <Button
                            size="sm"
                            variant="outline-light"
                            className="py-0 px-1"
                            onClick={async () => {
                              try {
                                await ApiService.api.delete(`/records/${record.record_id}/tags`, { data: { tags: [tag] } });
                                toast.info('Tag removed');
                                setTags((prev) => prev.filter((t) => t !== tag));
                              } catch (e) {
                                toast.error('Failed to remove tag');
                              }
                            }}
                            title="Remove tag"
                          >
                            <i className="fas fa-times"></i>
                          </Button>
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted mt-2">No tags</div>
                  )}
                </div>
              </div>
            </div>
          </Col>
        </Row>

        {/* Download Row */}
        <Row className="mb-4">
          <Col md={12}>
            {(record.raw_file_path || record.processed_file_path) ? (
              <div className="card h-100">
                <div className="card-body">
                  <h5 className="card-title mb-3">
                    <i className="fas fa-download me-2 text-primary"></i>
                    Download Logs
                  </h5>
                  <div className="d-flex flex-wrap gap-2">
                    {record.raw_file_path && (
                      <Button
                        variant="outline-primary"
                        onClick={() => handleDownload(record.raw_file_path)}
                        className="px-4 py-2"
                      >
                        <i className="fas fa-download me-2"></i>
                        Download Raw Log
                      </Button>
                    )}
                    {record.processed_file_path && (
                      <Button
                        variant="outline-primary"
                        onClick={() => handleDownload(record.processed_file_path)}
                        className="px-4 py-2"
                      >
                        <i className="fas fa-download me-2"></i>
                        Download Preprocessed Log
                      </Button>
                    )}
                    {record.genapi && record.genapi.analyzed && (
                      <Button
                        variant="outline-primary"
                        className="px-4 py-2"
                        onClick={() => {
                          try {
                            const data = record.genapi || {};
                            const pretty = JSON.stringify(data, null, 2);
                            const blob = new Blob([pretty], { type: 'application/json' });
                            const url = window.URL.createObjectURL(blob);
                            const link = document.createElement('a');
                            link.href = url;
                            const fname = `${record.record_id || 'analysis'}_analysis.json`;
                            link.download = fname;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            window.URL.revokeObjectURL(url);
                          } catch (e) {
                            console.error('Download analysis failed', e);
                          }
                        }}
                      >
                        <i className="fas fa-download me-2"></i>
                        Download Result
                      </Button>
                    )}
                  </div>
                  {record.processed_file_path && (
                    <p className="text-muted mt-3 mb-0">
                      <i className="fas fa-info-circle me-1"></i>
                      Download to view the preprocessed log/result content.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="card h-100">
                <div className="card-body d-flex align-items-center justify-content-center">
                  <span className="text-muted">No download options available</span>
                </div>
              </div>
            )}
          </Col>
        </Row>

        {/* Removed duplicate Problems section before Similar Records to avoid repetition */}

        {/* Similar Records */}
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="card-title mb-3">
              <i className="fas fa-search me-2 text-primary"></i>
              {(() => {
                const pct = (similarityMinInput !== '' ? parseFloat(similarityMinInput) : Math.round((similarityMin || 0) * 100)) || 0;
                return `Similar Records (≥ ${Math.max(0, Math.min(100, Math.round(pct)))}%)`;
              })()}
            </h5>
            <div className="d-flex align-items-center gap-2 mb-3">
              <label className="text-muted me-2" style={{ minWidth: 140 }}>Similarity threshold</label>
              <div className="input-group input-group-sm" style={{ maxWidth: 180 }}>
                <input
                  type="number"
                  className="form-control"
                  min={0}
                  max={100}
                  step={1}
                  value={similarityMinInput}
                  onChange={(e) => {
                    // Let the user freely edit; sanitize lightly to digits only
                    const val = e.target.value;
                    setSimilarityMinInput(val);
                  }}
                  onBlur={(e) => {
                    const val = e.target.value;
                    if (val === '') return;
                    let v = parseFloat(val);
                    if (isNaN(v)) {
                      setSimilarityMinInput('');
                    } else {
                      v = Math.max(0, Math.min(100, v));
                      setSimilarityMinInput(String(v));
                    }
                  }}
                />
                <span className="input-group-text">%</span>
              </div>
              <Button
                variant="outline-secondary"
                size="sm"
                className="ms-2"
                title="Search similar records"
                disabled={refreshingSimilar}
                onClick={async () => {
                  try {
                    setRefreshingSimilar(true);
                    let v = parseFloat(similarityMinInput);
                    if (isNaN(v)) v = 0;
                    v = Math.max(0, Math.min(100, v));
                    const minAsRatio = v / 100;
                    setSimilarityMin(minAsRatio);
                    const resp = await ApiService.getSimilarRecords(record.record_id, { min: minAsRatio, limit: 200 });
                    const similar = (resp.similar_records || [])
                      .filter(r => {
                        const s = r.similarity_score;
                        return (s > 1 ? s : s * 100) >= (minAsRatio * 100);
                      })
                      .sort((a, b) => {
                        const scoreA = a.similarity_score > 1 ? a.similarity_score : a.similarity_score * 100;
                        const scoreB = b.similarity_score > 1 ? b.similarity_score : b.similarity_score * 100;
                        return scoreB - scoreA;
                      });
                    setSimilarRecords(similar);
                  } catch (e) {
                    // ignore
                  } finally {
                    setRefreshingSimilar(false);
                  }
                }}
              >
                {refreshingSimilar ? 'Getting...' : 'Get records'}
              </Button>
            </div>
            {loadingSimilar ? (
              <div className="text-center py-4">
                <div className="loading-spinner mb-3"></div>
                <p className="text-muted">Loading similar records...</p>
              </div>
            ) : similarRecords.length === 0 ? (
              <p className="text-muted">No similar records found.</p>
            ) : (
              <>
                <div className="list-group" style={{ maxHeight: 360, overflowY: 'auto' }}>
                  {similarRecords.map((item, index) => {
                    const pct = (item.similarity_score > 1 ? item.similarity_score : item.similarity_score * 100).toFixed(1);
                    if (parseFloat(pct) < (similarityMin * 100)) return null; // enforce threshold in UI too
                    return (
                      <div key={index} className="list-group-item d-flex justify-content-between align-items-center">
                        <Button 
                          variant="link" 
                          className="p-0 text-decoration-none text-start flex-grow-1"
                          onClick={() => {
                            onHide();
                            window.location.href = `#record-${item.record_id}`;
                          }}
                          style={{ wordBreak: 'break-all' }}
                        >
                          {item.record_id}
                        </Button>
                        <Badge bg="primary" className="ms-2">{pct}%</Badge>
                      </div>
                    );
                  })}
                </div>
                {/* Removed See More button; list is now scrollable */}
              </>
            )}
          </div>
        </div>

        {/* Removed duplicate Summary card; use Analysis Summary within AI Analysis Results only */}

        {/* GenAPI Analysis Results - Detailed Analysis Section - Only show after real GenAPI analysis */}
        {analyzed && record.genapi && record.genapi.analyzed && 
         record.genapi.summary && 
         record.genapi.summary !== 'Log analysis completed with basic processing' &&
         (record.genapi.problems?.length > 0 || 
          record.genapi.key_insights?.length > 0 || 
          record.genapi.recommendations?.length > 0) && (
          <div className="card mb-4">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">
                <i className="fas fa-brain me-2"></i>
                AI Analysis Results
              </h5>
            </div>
            <div className="card-body">
              {/* Dev Feedback Banner + Analysis Summary */}
              <div className="mb-4">
                {(() => {
                  const considered = !!record?.genapi?.dev_feedback_considered;
                  const count = record?.genapi?.dev_feedback_hints_count || 0;
                  const sources = Array.isArray(record?.genapi?.dev_feedback_sources) ? record.genapi.dev_feedback_sources : [];
                  if (!considered) {
                    return (
                      <div className={`alert alert-secondary mb-3`}>No dev feedback is there to consider</div>
                    );
                  }
                  return (
                    <>
                      <div className="alert alert-warning mb-2" role="button" onClick={() => setShowDevSources((v) => !v)}>
                        Dev feedback found and considered ({count})
                        {sources && sources.length > 0 && (
                          <span className="ms-2 text-decoration-underline small">(click to {showDevSources ? 'hide' : 'view'} sources)</span>
                        )}
                      </div>
                      {showDevSources && sources && sources.length > 0 && (
                        <div className="mb-3">
                          <div className="list-group">
                            {sources.map((rid, idx) => (
                              <div key={rid || idx} className="list-group-item py-2 small">
                                <Button
                                  variant="link"
                                  className="p-0 text-decoration-none text-start"
                                  onClick={() => {
                                    try {
                                      onHide();
                                      window.location.href = `#record-${rid}`;
                                    } catch (e) {}
                                  }}
                                  style={{ wordBreak: 'break-all' }}
                                >
                                  {idx + 1}. {rid}
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
                <h6 className="text-primary mb-2">
                  <i className="fas fa-chart-line me-2"></i>
                  Analysis Summary
                </h6>
                <div className="alert alert-info">
                  <p className="mb-0">{record.genapi.summary || 'No summary available'}</p>
                </div>
              </div>

              {/* Problems Found */}
              {record.genapi.problems && record.genapi.problems.length > 0 ? (
                <div className="mb-4">
                  <h6 className="text-primary mb-3">
                    <i className="fas fa-exclamation-triangle me-2"></i>
                    Problems Found ({record.genapi.problems.length})
                  </h6>
                  {record.genapi.problems.map((problem, index) => (
                    <div key={index} className="card mb-3 border-start border-4 border-danger">
                      <div className="card-body">
                        <div className="d-flex justify-content-between align-items-start mb-3">
                          <h6 className="card-title mb-0 text-danger">{problem.title}</h6>
                          <Badge className={`severity-${getSeverityClass(problem.severity)}`}>
                            {getSeverityText(problem.severity)} ({problem.severity}/100)
                          </Badge>
                        </div>
                        
                        <div className="row">
                          <div className="col-md-6">
                            <p className="mb-2">
                              <strong>Root Cause:</strong><br/>
                              <span className="text-muted">{problem.root_cause || 'Not specified'}</span>
                            </p>
                          </div>
                          <div className="col-md-6">
                            <p className="mb-2">
                              <strong>Signals:</strong><br/>
                              <span className="text-muted">{problem.signals?.join(', ') || 'None detected'}</span>
                            </p>
                          </div>
                        </div>

                        {problem.raw_log && problem.raw_log.length > 0 && (
                          <div className="mt-3">
                            <strong>Relevant Log Lines:</strong>
                            <div className="mt-2 p-3 bg-dark text-light rounded" style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>
                              {problem.raw_log.map((logLine, logIndex) => (
                                <div key={logIndex} className="mb-1">{logLine}</div>
                              ))}
                            </div>
                          </div>
                        )}

                        {problem.recommendations && (
                          <div className="mt-3">
                            <strong>Recommendations:</strong>
                            <p className="mb-0 mt-1 text-success">{problem.recommendations}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mb-4">
                  <Alert variant="success">
                    <i className="fas fa-check-circle me-2"></i>
                    <strong>No problems detected!</strong> Your log appears to be clean and healthy.
                  </Alert>
                </div>
              )}

              {/* Key Insights */}
              {record.genapi.key_insights && record.genapi.key_insights.length > 0 && (
                <div className="mb-4">
                  <h6 className="text-primary mb-3">
                    <i className="fas fa-lightbulb me-2"></i>
                    Key Insights
                  </h6>
                  <div className="list-group">
                    {record.genapi.key_insights.map((insight, index) => (
                      <div key={index} className="list-group-item">
                        <i className="fas fa-arrow-right me-2 text-primary"></i>
                        {insight}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {record.genapi.recommendations && record.genapi.recommendations.length > 0 && (
                <div className="mb-4">
                  <h6 className="text-primary mb-3">
                    <i className="fas fa-tasks me-2"></i>
                    General Recommendations
                  </h6>
                  <div className="list-group">
                    {record.genapi.recommendations.map((rec, index) => (
                      <div key={index} className="list-group-item">
                        <i className="fas fa-check-circle me-2 text-success"></i>
                        {rec}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Analysis Metadata */}
              <div className="mt-4 pt-3 border-top">
                <div className="row text-muted small">
                  <div className="col-md-6">
                    <i className="fas fa-clock me-1"></i>
                    Analysis completed: {record.genapi.analyzed_at ? new Date(record.genapi.analyzed_at).toLocaleString() : 'Unknown'}
                  </div>
                  <div className="col-md-6 text-end">
                    <i className="fas fa-robot me-1"></i>
                    Powered by GenAPI AI
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="card">
          <div className="card-body">
            <div className="d-flex gap-3 flex-wrap">
              <Button 
                variant="primary" 
                onClick={onAnalyze} 
                className="px-4 py-2"
                disabled={isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <i className="fas fa-spinner fa-spin me-2"></i>
                    Analyzing... ({Math.round(analysisProgress || 0)}%)
                  </>
                ) : (
                  <>
                    <i className="fas fa-brain me-2"></i>
                    Analyze with GenAPI
                  </>
                )}
              </Button>
              <Button variant="success" onClick={() => setShowChat(true)} className="px-4 py-2">
                <i className="fas fa-comments me-2"></i>
                Ask a Question
              </Button>
            </div>
          </div>
        </div>

        {/* Dev Feedback Section (moved below action buttons) */}
        <div className="card mt-4">
          <div className="card-body">
            <h5 className="card-title mb-3">
              <i className="fas fa-sticky-note me-2 text-primary"></i>
              Dev Feedback
            </h5>
            <Alert variant="danger" className="mb-3 py-2 px-3 small">
              <i className="fas fa-exclamation-triangle me-2"></i>
              Make sure you understand how this works — it can affect future log analyses.
            </Alert>
            <div className="mt-1">
              <textarea
                className="form-control"
                rows="6"
                placeholder="Add developer notes about known bugs, patterns, mitigations... (use Save to persist)"
                style={{ minHeight: 150, maxHeight: 260, overflowY: 'auto' }}
                value={devFeedbackText}
                onChange={(e) => setDevFeedbackText(e.target.value)}
              />
              <div className="mt-2 d-flex justify-content-end gap-2">
                <Button
                  variant="outline-secondary"
                  size="sm"
                  disabled={savingDevFeedback || (record?.dev_feedback === devFeedbackText)}
                  onClick={async () => {
                    try {
                      setSavingDevFeedback(true);
                      await ApiService.updateRecordDevFeedback(record.record_id, devFeedbackText);
                      if (record) {
                        record.dev_feedback = devFeedbackText;
                      }
                      toast.success('Dev feedback saved');
                    } catch (err) {
                      toast.error('Failed to save dev feedback');
                    } finally {
                      setSavingDevFeedback(false);
                    }
                  }}
                >
                  {savingDevFeedback ? (
                    <>
                      <i className="fas fa-spinner fa-spin me-1"></i>
                      Saving
                    </>
                  ) : (
                    <>Save</>
                  )}
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  disabled={savingDevFeedback || !devFeedbackText}
                  onClick={() => setDevFeedbackText('')}
                >
                  Clear
                </Button>
              </div>
              <div className="mt-3 d-flex align-items-center gap-2">
                <label className="text-muted" style={{ minWidth: 180 }}>Dev feedback threshold</label>
                <div className="input-group input-group-sm" style={{ maxWidth: 180 }}>
                  <input
                    type="number"
                    className="form-control"
                    min={0}
                    max={100}
                    step={1}
                    value={devFeedbackThresholdInput}
                    placeholder={typeof record?.dev_feedback_threshold === 'number' ? String(record.dev_feedback_threshold) : '70'}
                    onChange={(e) => setDevFeedbackThresholdInput(e.target.value)}
                  />
                  <span className="input-group-text">%</span>
                </div>
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={async () => {
                    try {
                      let v = parseFloat(devFeedbackThresholdInput);
                      if (isNaN(v)) v = (typeof record?.dev_feedback_threshold === 'number' ? record.dev_feedback_threshold : 70);
                      v = Math.max(0, Math.min(100, v));
                      const res = await ApiService.updateRecordDevFeedbackThreshold(record.record_id, v);
                      if (record) {
                        record.dev_feedback_threshold = v;
                      }
                      toast.success('Dev feedback threshold saved');
                    } catch (e) {
                      toast.error('Failed to save threshold');
                    }
                  }}
                >
                  Save
                </Button>
              </div>
              <p className="text-muted mt-2 mb-0" style={{ fontSize: '0.85rem' }}>
                These notes will be used to guide future AI analyses, including hints from similar records.
              </p>
            </div>
          </div>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>

      {/* Removed See More modal; list is scrollable inline */}
    </Modal>
    
    {/* Chat Modal */}
    <ChatModal
      record={record}
      show={showChat}
      onHide={() => setShowChat(false)}
    />
  </>
  );
};

export default RecordModal;
