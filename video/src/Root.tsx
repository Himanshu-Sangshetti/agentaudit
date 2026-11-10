import React from 'react';
import {Composition} from 'remotion';
import {AgentAudit, TOTAL} from './Video';

export const Root: React.FC = () => (
  <Composition id="AgentAudit" component={AgentAudit} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
);
