import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import ApiService from '../services/ApiService';

const UploadArea = ({ onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [job, setJob] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [context, setContext] = useState('');
  const [visibility, setVisibility] = useState(() => {
    return localStorage.getItem('pref_visibility') || 'self';
  });
  // Use a ref to avoid stale closures causing multiple success callbacks
  const successCallbackCalledRef = useRef(false);
  const intervalRef = useRef(null);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    await handleUpload(file);
  }, [context, visibility]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.log', '.txt', '.out', '.err'],
      'application/octet-stream': ['.log', '.txt', '.out', '.err']
    },
    multiple: false,
    disabled: uploading
  });

  const handleUpload = async (file) => {
    try {
      setUploading(true);
      toast.info('Uploading log file...');
      
      console.log('Uploading file:', file.name, 'Size:', file.size);
      
      // Just store the file for now, don't process yet
      setUploadedFile(file);
      toast.success('Log file uploaded successfully! Review and click Submit to process.');
      
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Upload failed: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async () => {
    if (!uploadedFile) {
      toast.error('Please upload a file first');
      return;
    }

    try {
      setProcessing(true);
      successCallbackCalledRef.current = false; // Reset for a new upload
      toast.info('Processing log file...');
      
      console.log('Processing file:', uploadedFile.name, 'Visibility:', visibility);
      const response = await ApiService.uploadLog(uploadedFile, context, visibility);
      console.log('Upload response:', response);
      
      if (response.job_id) {
        toast.success('Log processing started! Please wait...');
        setJob({ id: response.job_id, status: 'queued', progress: 0 });
        // Expose job info globally so Dashboard can show a persistent card
        window.__activeJob = { id: response.job_id };
        // Poll job status
        pollJobStatus(response.job_id);
        setContext(''); // Clear context after successful upload
        setUploadedFile(null); // Clear uploaded file
      } else {
        throw new Error(response.error || 'Processing failed');
      }
    } catch (error) {
      console.error('Processing error:', error);
      toast.error('Processing failed: ' + error.message);
    } finally {
      setProcessing(false);
    }
  };

  const pollJobStatus = async (jobId) => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    let isCompleted = false;
    
    try {
      const check = async () => {
        if (isCompleted) return; // Stop checking if already completed
        
        try {
          const res = await fetch(`http://localhost:5000/jobs/${jobId}`, {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`
            }
          });
          const data = await res.json();
          setJob(data);
          window.__activeJob = data;
          
          if (data.status === 'completed' || data.status === 'failed') {
            isCompleted = true; // Mark as completed
            setUploading(false);
            
            if (data.status === 'completed' && data.record_id && onUploadSuccess && !successCallbackCalledRef.current) {
              // Ensure we call success callback only once
              successCallbackCalledRef.current = true;
              try {
                onUploadSuccess({ record_id: data.record_id });
              } catch (e) {
                // no-op
              }
            } else if (data.status === 'failed') {
              toast.error('Log processing failed: ' + (data.error || 'Unknown error'));
            }
            
            // Clear the active job immediately when completed
            window.__activeJob = null;
            
            // Stop the polling interval
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        } catch (e) {
          console.error('Error checking job status:', e);
        }
      };
      
      // Initial check then every 1.5s
      await check();
      
      if (!isCompleted) {
        intervalRef.current = setInterval(async () => {
          if (!jobId || isCompleted) {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            return;
          }
          await check();
        }, 1500);
      }
    } catch (e) {
      console.error('Error in pollJobStatus:', e);
    }
  };

  const handleManualUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      onDrop([file]);
    }
  };

  // Visibility helpers for chip/tooltip and preference persistence
  const visMeta = {
    self:   { label: 'Private', color: '#6c757d', icon: 'fas fa-lock',  desc: 'Only you can view and analyze this log.' },
    team:   { label: 'Team',    color: '#0d6efd', icon: 'fas fa-users', desc: 'Visible to your team members.' },
    public: { label: 'Public',  color: '#198754', icon: 'fas fa-globe', desc: 'Anyone in the system can view.' }
  };
  const currentVis = visMeta[visibility] || visMeta.self;

  const onChangeVisibility = (val) => {
    if (uploading || processing) return;
    setVisibility(val);
    localStorage.setItem('pref_visibility', val);
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex align-items-center mb-4">
          <div className="d-inline-flex align-items-center justify-content-center rounded-circle bg-primary text-white me-3" 
               style={{ width: '50px', height: '50px', fontSize: '1.2rem' }}>
            <i className="fas fa-upload"></i>
          </div>
          <div>
            <h5 className="card-title mb-1 fw-bold">Upload Log File</h5>
            <p className="text-muted mb-0">Drag & drop or click to browse</p>
          </div>
        </div>
        
        {uploadedFile ? (
          // Show uploaded file with submit button
          <div className="uploaded-file-preview">
            <div className="d-flex align-items-center justify-content-between p-3 border rounded bg-light">
              <div className="d-flex align-items-center">
                <div className="me-3">
                  <i className="fas fa-file-alt text-primary" style={{ fontSize: '2rem' }}></i>
                </div>
                <div>
                  <h6 className="mb-1 fw-bold">{uploadedFile.name}</h6>
                  <p className="mb-0 text-muted small">
                    {(uploadedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setUploadedFile(null)}
                  disabled={processing}
                >
                  <i className="fas fa-times me-1"></i>
                  Remove
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={processing}
                >
                  {processing ? (
                    <>
                      <div className="loading-spinner me-2" style={{ width: '16px', height: '16px' }}></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-play me-2"></i>
                      Submit for Processing
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Show upload area
          <div
            {...getRootProps()}
            className={`upload-area ${isDragActive ? 'dragover' : ''} ${uploading ? 'disabled' : ''}`}
          >
            <input {...getInputProps()} />
            <div className="text-center">
              {uploading ? (
                <>
                  <div className="loading-spinner mb-3"></div>
                  <h6>Uploading your log file...</h6>
                  <p className="text-muted">Please wait</p>
                </>
              ) : isDragActive ? (
                <>
                  <div className="mb-4">
                    <div className="d-inline-flex align-items-center justify-content-center rounded-circle bg-primary text-white" 
                         style={{ width: '80px', height: '40px', fontSize: '2rem' }}>
                      <i className="fas fa-cloud-upload-alt"></i>
                    </div>
                  </div>
                  <h5 className="fw-bold text-primary mb-2">Drop the log file here</h5>
                  <p className="text-muted fs-5">Release to upload</p>
                </>
              ) : (
                <>
                  <div className="mb-4">
                    <div className="d-inline-flex align-items-center justify-content-center rounded-circle bg-light text-muted" 
                         style={{ width: '80px', height: '40px', fontSize: '2rem' }}>
                      <i className="fas fa-cloud-upload-alt"></i>
                    </div>
                  </div>
                  <h5 className="fw-bold mb-2">Drag & drop your log file here</h5>
                  <p className="text-muted fs-5 mb-4">or click to browse</p>
                  <button 
                    type="button" 
                    className="btn btn-outline-primary"
                    disabled={uploading || processing}
                  >
                    <i className="fas fa-folder-open me-2"></i>
                    Choose File
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Progress card moved to Dashboard for a single persistent view */}

        <div className="mt-3">
          <label htmlFor="context" className="form-label">
            <i className="fas fa-comment me-1"></i>
            Context (Optional)
          </label>
          <textarea
            id="context"
            className="form-control"
            rows="2"
            placeholder="Provide additional context about this log file..."
            value={context}
            onChange={(e) => setContext(e.target.value)}
            disabled={uploading || processing}
          />
          <small className="form-text text-muted">
            Add any relevant information about when, where, or why this log was generated
          </small>
        </div>

        <div className="mt-3">
          <label htmlFor="visibility" className="form-label d-flex align-items-center">
            <i className="fas fa-eye me-1"></i>
            Visibility
            <span
              className="ms-2 px-2 py-1 rounded-pill"
              style={{ background: currentVis.color, color: '#fff', fontSize: '0.75rem' }}
              title={currentVis.desc}
            >
              <i className={`${currentVis.icon} me-1`}></i>{currentVis.label}
            </span>
          </label>

          <div className="d-flex align-items-center gap-2">
            <select
              id="visibility"
              className="form-select"
              value={visibility}
              onChange={(e) => onChangeVisibility(e.target.value)}
              disabled={uploading || processing}
              title={currentVis.desc}
              style={{ maxWidth: 280 }}
            >
              <option value="self" title={visMeta.self.desc}>Private (Only Me)</option>
              <option value="team" title={visMeta.team.desc}>Team (My Team Members)</option>
              <option value="public" title={visMeta.public.desc}>Public (Everyone)</option>
            </select>

            <div className="form-check d-flex align-items-center ms-1" title="Remember this choice for next uploads">
              <input
                className="form-check-input"
                type="checkbox"
                id="rememberVis"
                defaultChecked={!!localStorage.getItem('pref_visibility')}
                onChange={(e) => {
                  if (!e.target.checked) localStorage.removeItem('pref_visibility');
                  else localStorage.setItem('pref_visibility', visibility);
                }}
                disabled={uploading || processing}
              />
              <label className="form-check-label ms-1" htmlFor="rememberVis">Remember</label>
            </div>
          </div>

          <small className="form-text text-muted d-block mt-1">
            {currentVis.desc}
          </small>
        </div>

        <div className="mt-3">
          <small className="text-muted">
            <i className="fas fa-info-circle me-1"></i>
            Supported formats: .log, .txt, .out, .err | Max size: 50MB
          </small>
        </div>
      </div>
    </div>
  );
};

export default UploadArea;
