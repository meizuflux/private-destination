import { createContext, useContext, Component } from "solid-js";
import { createStore } from "solid-js/store";

export const StoreContext = createContext()

export function Provider(props) {
    const [state, setState] = createStore({ user: null, count: 0 })
    const store = [
        state,
        {
            increment() {
                setState("count", (c) => c + 1);
              },
              decrement() {
                setState("count", (c) => c - 1);
              },
        }
    ]
    return (
        <StoreContext.Provider value={store}>
            {props.children}
        </StoreContext.Provider>
    )
}


type CounterStore = [
  { count: number },
  { increment?: () => void; decrement?: () => void }
];

const CounterContext = createContext<CounterStore>([{ count: 0 }, {}]);

export const CounterProvider: Component<{ count: number }> = (props) => {
  const [state, setState] = createStore({ count: props.count || 0 }),
    store: CounterStore = [
      state,
      {
        increment() {
          setState("count", (c) => c + 1);
        },
        decrement() {
          setState("count", (c) => c - 1);
        }
      }
    ];

  return (
    <CounterContext.Provider value={store}>
      {props.children}
    </CounterContext.Provider>
  );
};

export function useStore() {
    return useContext(CounterContext)
}

export function useCounter() {
    return useContext(CounterContext);
}