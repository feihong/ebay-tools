/*
Generated from this page: http://loov.io/jsfx/

*/

let soundEffectsLibrary = {
  "success": {
    "Generator": {
      "Func": "sine"
    },
    "Volume": {
      "Sustain": 0.06431111267228035,
      "Punch": 0.5994517605679162,
      "Decay": 0.4117447464916866
    },
    "Frequency": {
      "ChangeSpeed": 0.12442875796416693,
      "ChangeAmount": 10.613664003016508,
      "Start": 1124.225592378399
    }
  },
  "error": {
    "Volume": {
      "Sustain": 0.20181592698349404,
      "Decay": 0.3640179788905873
    },
    "Generator": {
      "A": 0.38170758961805135,
      "Func": "sine"
    },
    "Frequency": {
      "Slide": 0.16911265266878778,
      "Start": 538.0564181094517
    },
    "Vibrato": {
      "Frequency": 39.643358681146665,
      "Depth": 0.5696703010481962
    }
  },
  "failure": {
    "Volume": {
      "Sustain": 0.2013428942164524,
      "Punch": 0.7247186990164947,
      "Decay": 0.671
    },
    "Generator": {
      "Func": "noise"
    },
    "Frequency": {
      "Slide": -0.3426021495630788,
      "Start": 910.4436565942931
    }
  }
}

window.sfx = window.jsfx.Sounds(soundEffectsLibrary)
