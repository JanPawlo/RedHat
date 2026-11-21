import { useEffect, useState } from 'react';
import { analysis as mockAnalysis } from '../data/mockData.js';
import { getAnalysis } from '../api/analysisApi.js';

let cached = null;
let request = null;

function loadAnalysis() {
  if (!request) {
    request = getAnalysis()
      .then((data) => {
        cached = data;
        return data;
      })
      .catch(() => {
        request = null;
        return null;
      });
  }
  return request;
}

/** Analysis page data from the database (bank statement + invoices); the mock until it arrives or when the API fails. */
export function useAnalysis() {
  const [data, setData] = useState(cached);

  useEffect(() => {
    let active = true;
    loadAnalysis().then((next) => active && next && setData(next));
    return () => {
      active = false;
    };
  }, []);

  return data || mockAnalysis;
}

