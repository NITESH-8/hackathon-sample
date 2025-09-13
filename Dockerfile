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




/* Uploaded file preview styles */
.uploaded-file-preview {
  margin-bottom: 1rem;
}

.uploaded-file-preview .border {
  border-color: #dee2e6 !important;
  transition: all 0.3s ease;
}

.uploaded-file-preview .border:hover {
  border-color: #0d6efd !important;
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

.uploaded-file-preview .btn {
  transition: all 0.3s ease;
}

.uploaded-file-preview .btn:hover {
  transform: translateY(-1px);
}

/* Loading spinner for submit button */
.uploaded-file-preview .loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #ffffff;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
