const tolInput = document.getElementById('tolerance');
const camSelect = document.getElementById('cameraSelect');
const stream = document.getElementById('stream');
const tolVal = document.getElementById('tolVal');

function reload() {
  const cam = camSelect.value;
  const tol = tolInput.value;
  tolVal.innerText = tol;
  stream.src = `/video_feed?cam=${cam}&tol=${tol}`;
}

tolInput.addEventListener('input', reload);
camSelect.addEventListener('change', reload);