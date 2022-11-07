const mongoose = require("mongoose");

const positionSchema = new mongoose.Schema({
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

// connect positionSchema with the "positions" collection
module.exports = mongoose.model("Position", positionSchema);
