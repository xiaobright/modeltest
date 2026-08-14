export const MINIMAL_SYSTEM = 'You are a helpful software engineer assistant.'

export const PARAPHRASED_SYSTEM =
  'You are an assistant that helps with software engineering tasks.'

export const USER_PROMPT = `Inspect the current repository before answering.
First determine its top-level structure, then locate and read the project README.
Do not guess from prior knowledge. Use the available tools first.`

export function buildMinimalTools() {
  return [
    {
      type: 'function',
      function: {
        name: 'bash',
        description: 'Run a command in a persistent shell.',
        parameters: {
          type: 'object',
          properties: { command: { type: 'string' } },
          required: ['command'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'read',
        description: 'Read a text file.',
        parameters: {
          type: 'object',
          properties: { path: { type: 'string' } },
          required: ['path'],
        },
      },
    },
  ]
}
