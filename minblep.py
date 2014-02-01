#!/usr/bin/env python

from __future__ import division
import numpy as np, logging

log = logging.getLogger(__name__)

class MinBlep:

  def __init__(self, zeros, scale):
    def normintegral(signal):
      return np.cumsum(signal) / scale
    self.midpoint = zeros * scale # Index of peak of sinc.
    self.size = self.midpoint * 2 + 1
    x = 2 * zeros * np.arange(self.size) / (self.size - 1) - zeros
    # The sinc starts and ends with zero, and the window fixes the integral height:
    self.bli = np.blackman(self.size) * np.sinc(x)
    self.blep = normintegral(self.bli)
    # Everything is real after we discard the phase info here:
    absdft = np.abs(np.fft.fft(self.bli))
    realcepstrum = np.fft.ifft(np.log(absdft)) # Symmetric apart from first element.
    # Leave first point, zero max phase part, double min phase part to compensate:
    realcepstrum[1:self.midpoint + 1] *= 2
    realcepstrum[self.midpoint + 1:] = 0
    self.minbli = np.fft.ifft(np.exp(np.fft.fft(realcepstrum))).real
    # Check our cepstrum manipulation isn't broken:
    if not np.allclose(absdft, np.abs(np.fft.fft(self.minbli))):
      log.warn('Bad min-phase reconstruction.')
    self.minblep = normintegral(self.minbli)

def main():
  import matplotlib.pyplot as plt
  minblep = MinBlep(10, 5)
  plt.plot(minblep.bli, 'b+')
  plt.plot(minblep.blep, 'bo')
  plt.plot(np.arange(minblep.size) + minblep.midpoint, minblep.minbli, 'r+')
  for style in 'r', 'ro':
    plt.plot(np.arange(minblep.size) + minblep.midpoint, minblep.minblep, style)
  plt.grid(True)
  plt.show()

if __name__ == '__main__':
  main()
