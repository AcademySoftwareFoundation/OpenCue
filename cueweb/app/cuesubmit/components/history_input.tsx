/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use client";

import * as React from "react";

import { loadHistory, type HistoryField } from "../lib/history";

// Text input with a native <datalist> dropdown of previously-submitted
// values. Mirrors the cache cuesubmit Python builds up on disk so
// users get the same "start typing -> see your previous values"
// affordance.
//
// Loads history from localStorage on mount AND when the window's
// `cueweb:cuesubmit-history-changed` event fires (so a successful
// submit can broadcast "new entries added" and any open inputs
// refresh without remount).

export const HISTORY_CHANGED_EVENT = "cueweb:cuesubmit-history-changed";

type Props = Omit<React.InputHTMLAttributes<HTMLInputElement>, "list"> & {
  historyField: HistoryField;
};

export const HistoryInput = React.forwardRef<HTMLInputElement, Props>(
  function HistoryInput({ historyField, id, ...rest }, ref) {
    const listId = React.useId();
    const [items, setItems] = React.useState<string[]>([]);

    React.useEffect(() => {
      setItems(loadHistory(historyField));
      const handler = () => setItems(loadHistory(historyField));
      window.addEventListener(HISTORY_CHANGED_EVENT, handler);
      return () => window.removeEventListener(HISTORY_CHANGED_EVENT, handler);
    }, [historyField]);

    return (
      <>
        <input ref={ref} id={id} list={listId} {...rest} />
        <datalist id={listId}>
          {items.map((v) => (
            <option key={v} value={v} />
          ))}
        </datalist>
      </>
    );
  },
);
