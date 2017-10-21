$('a.download-awaiting').on('click', evt => {
  evt.preventDefault()
  $.get('/commands/download-awaiting/', reloadIfSuccess)
})

$('a.write-packing').on('click', evt => {
  evt.preventDefault()
  $.get('/commands/write-packing/', reloadIfSuccess)
})

function reloadIfSuccess(data) {
  if (data === 'ok') {
    sfx.success()
    setTimeout(() => window.location.reload(true), 1000)
  }
}
