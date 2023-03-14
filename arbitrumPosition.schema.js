const mongoose = require("mongoose");

const arbitrumPositionSchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  date: {
    type: String,
    required: true,
  },
  collateralInOVLBetween0and10: {
    type: Number,
    required: true,
  },
  collateralInOVLBetween11and20: {
    type: Number,
    required: true,
  },
  collateralInOVLBetween21and100: {
    type: Number,
    required: true,
  },
  collateralInOVLBetween101and500: {
    type: Number,
    required: true,
  },
  collateralInOVLBetween501and1000: {
    type: Number,
    required: true,
  },
});

// connect arbitrumPositionSchema with the "arbitrumposition" collection
module.exports = mongoose.model("arbitrumPosition", arbitrumPositionSchema);
