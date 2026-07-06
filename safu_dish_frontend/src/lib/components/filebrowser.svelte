<script>
  export let control;

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('routing_key', control.routing_key);  // Optional, depending on UI logic

    const res = await fetch('/api/modules/data_parser/document/upload_and_parse', {
      method: 'POST',
      body: formData
    });

    const json = await res.json();
    if (json.status !== 'success') {
      console.error("❌ Upload and parse failed:", json);
      return;
    }

    // Optional: Emit to docbox or trigger display
    console.log("✅ Parsed document:", json.reply);
  };
</script>

<div class="file-upload-wrapper">
  <label for="fileInput" class="upload-label">📁 Upload File</label>
  <input
    id="fileInput"
    type="file"
    class="hidden-input"
    on:change={handleFileSelect}
    accept={control.filetypes?.join(',') || '*/*'}
  />
</div>

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  .file-upload-wrapper {
    display: inline-block;
    position: relative;
    margin-top: 1rem;
  }

  .upload-label {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    font-family: 'OCR A Extended', monospace;
    background-color: #111;
    border: 1px solid #0ff;
    color: #0ff;
    cursor: pointer;
    border-radius: 6px;
    text-shadow: 0 0 1px #0ff, 0 0 7px #0ff;
    box-shadow: 0 0 6px #0ff, 0 0 14px #0ff3;
    transition: transform 0.2s ease, box-shadow 0.3s ease;
  }

  .upload-label:hover {
    transform: scale(1.05);
    box-shadow: 0 0 10px #0ff, 0 0 18px #0ff8;
  }

  .upload-label:active {
    transform: scale(0.96);
    box-shadow: inset 0 0 6px #0ff;
  }

  .hidden-input {
    display: none;
  }
</style>
