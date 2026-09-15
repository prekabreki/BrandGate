package main

import (
	"context"
	"io"
	"os"
	"strings"
	"time"
)

// watchFile tails path and hands every complete new line to handle. It starts
// at the END of the file: the rows already there are history, and history is
// never replayed on a restart. The posted-state file covers the other half of
// that promise, for rows appended while the relay was down but never posted.
func watchFile(ctx context.Context, path string, every time.Duration, handle func(line string)) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	offset, err := f.Seek(0, io.SeekEnd)
	if err != nil {
		return err
	}
	var partial strings.Builder
	tick := time.NewTicker(every)
	defer tick.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-tick.C:
		}
		st, err := f.Stat()
		if err != nil {
			return err
		}
		if st.Size() < offset {
			// The file was truncated or rotated. Start over from its beginning
			// rather than reading garbage from an old offset.
			offset = 0
			partial.Reset()
		}
		if st.Size() == offset {
			continue
		}
		buf := make([]byte, st.Size()-offset)
		n, err := f.ReadAt(buf, offset)
		if err != nil && err != io.EOF {
			return err
		}
		offset += int64(n)
		partial.Write(buf[:n])
		text := partial.String()
		partial.Reset()
		for {
			i := strings.IndexByte(text, '\n')
			if i < 0 {
				partial.WriteString(text)
				break
			}
			handle(text[:i])
			text = text[i+1:]
		}
	}
}
