$('a.download-awaiting').on('click', evt => {
  evt.preventDefault()

  $.get('/commands/download-awaiting/', data => {
    if (data === 'ok') {
      sfx.success()
    }
  })
})
